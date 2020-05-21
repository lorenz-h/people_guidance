import cv2
import numpy as np

from .config import *

class Matcher():
    def __init__(self, max_num_features, logger, K, method='FAST', use_E=True):
        self.curr_img = None
        self.curr_kps = None
        self.curr_desc = None
        self.prev_img = None
        self.prev_kps = None
        self.prev_desc = None

        self.logger = logger
        self.intrinsic_matrix = K
        self.method = method
        self.use_E = use_E
        self.nb_transform_solutions = 0
        self.rotations = np.empty((0,3,4))
        self.translations = np.empty((0,3,1))

        self.detector = featureDetector(max_num_features, logger, method=self.method)
        self.should_initialize = True

    def initialize(self, img):
        self.prev_img = img
        self.prev_kps, self.prev_desc = self.detector.detect(img)
        self.should_initialize = False

    def step(self):
        self.prev_img = self.curr_img
        self.prev_kps = self.curr_kps
        self.prev_desc = self.curr_desc

    def match(self, img):
        raise NotImplementedError

    def calcTransformation(self, mp1, mp2):
        if not self.use_E:
            # if we found enough matches do a RANSAC search to find inliers corresponding to one homography
            H, mask = cv2.findHomography(mp1, mp2, cv2.RANSAC, 1.0)
            self.nb_transform_solutions, self.rotations, self.translations, _ = cv2.decomposeHomographyMat(H, self.intrinsic_matrix)
            return mask
        else:
            E, mask = cv2.findEssentialMat(mp1, mp2, self.intrinsic_matrix, cv2.RANSAC, 0.999, 1.0, None)
            _, self.rotations, self.translations, _ = cv2.recoverPose(E, mp1, mp2, self.intrinsic_matrix, mask)
            self.nb_transform_solutions = 1
            return mask

    def getTransformations(self):
        if self.nb_transform_solutions > 0:
            transformations = np.zeros((self.nb_transform_solutions, 3, 4))
            for i in range(self.nb_transform_solutions):
                transformations[i, :, 0:3] = self.rotations
                transformations[i, :, 3] = self.translations.ravel()
            return transformations
        else:
            return np.zeros((1,3,4))

class bruteForceMatcher(Matcher):
    def __init__(self, max_num_features, logger, K, method='FAST', use_E=True):
        super().__init__(max_num_features, logger, K, method, use_E)
        
        matching_norm = None
        if self.method=='ORB':
            matching_norm = cv2.NORM_HAMMING
        elif method=='FAST' or method=='SHI-TOMASI':
            self.logger.warn("FAST and SHI-TOMASI features are not supported for simple feature matching, switching to ORB...")
            self.method='ORB'
            matching_norm = cv2.NORM_HAMMING
        elif method=='SIFT' or method=='SURF':
            matching_norm = cv2.NORM_L2

        self.matcher = cv2.BFMatcher_create(matching_norm, crossCheck=True)

    def match(self, img):
        self.curr_img = img
        prev_match_pts, curr_match_pts = self.bruteForceMatching()

        if self.prev_kps.shape[0] > 0:
            mask = self.calcTransformation(prev_match_pts, curr_match_pts)
        else:
            mask = np.array([])

        prev_match_pts = prev_match_pts[mask.ravel().astype(bool)]
        curr_match_pts = curr_match_pts[mask.ravel().astype(bool)]

        self.step()

        return prev_match_pts, curr_match_pts

    def bruteForceMatching(self):
        self.curr_kps, self.curr_desc = self.detector.detect(self.curr_img)
        matches = self.matcher.match(self.prev_desc, self.curr_desc)

        old_match_points = np.array([self.prev_kps[match.queryIdx] for match in matches]).reshape((-1, 2))
        new_match_points = np.array([self.curr_kps[match.trainIdx] for match in matches]).reshape((-1, 2))

        return old_match_points, new_match_points

class opticalFlowMatcher(Matcher):
    def match(self, img):
        self.curr_img = img

        if self.prev_kps.shape[0] < OF_MIN_NUM_FEATURES:
            self.prev_kps, _ = self.detector.detect(self.prev_img)

        # mp1, mp2, diff = self.KLT_featureTracking(img)
        self.prev_kps, self.curr_kps, diff = self.KLT_featureTracking()

        # If difference is small we skip the frame (not much movement)
        if self.skip_frame(diff):
                self.logger.info("skipping frame")
                return np.array([]), np.array([])

        if self.prev_kps.shape[0] > 0:
            mask = self.calcTransformation(self.prev_kps, self.curr_kps)
        else:
            mask = np.array([])

        self.prev_kps = self.prev_kps[mask.ravel().astype(bool)]
        self.curr_kps = self.curr_kps[mask.ravel().astype(bool)]

        prev_match_points = self.prev_kps
        self.step()

        return prev_match_points, self.curr_kps

    def KLT_featureTracking(self):
        """Feature tracking using the Kanade-Lucas-Tomasi tracker.
        """
        # Feature Correspondence with Backtracking Check
        kp2, status, error = cv2.calcOpticalFlowPyrLK(self.prev_img, self.curr_img, self.prev_kps, None, **lk_params)
        kp1, status, error = cv2.calcOpticalFlowPyrLK(self.curr_img, self.prev_img, kp2, None, **lk_params)

        d = abs(self.prev_kps - kp1).reshape(-1, 2).max(-1)  # Verify the absolute difference between feature points
        good = d < OF_MIN_MATCHING_DIFF

        # Error Management
        if len(d) == 0:
            self.logger.warning('No point correspondance.')
            self.should_initialize = True
        elif list(good).count(True) <= 5:  # If less than 5 good points, it uses the features obtain without the backtracking check
            self.logger.warning('Few point correspondances')
            return kp1, kp2, OF_DIFF_THRESHOLD

        # Create new lists with the good features
        n_kp1, n_kp2 = [], []
        for i, good_flag in enumerate(good):
            if good_flag:
                n_kp1.append(kp1[i])
                n_kp2.append(kp2[i])

        # Format the features into float32 numpy arrays
        n_kp1, n_kp2 = np.array(n_kp1, dtype=np.float32), np.array(n_kp2, dtype=np.float32)

        # Verify if the point correspondence points are in the same pixel coordinates
        d = abs(n_kp1 - n_kp2).reshape(-1, 2).max(-1)

        # The mean of the differences is used to determine the amount of distance between the pixels
        diff_mean = np.mean(d)

        return n_kp1, n_kp2, diff_mean

    def skip_frame(self, diff):
        """ Skip a frame if the difference is smaller than a certain value.
            Small difference means the frame almost did not change.
        """
        if diff == 0.0:
            # 0.0 diff is an error, don't skip
            return False
        else:
            return diff < OF_DIFF_THRESHOLD

class featureDetector:
    def __init__(self, max_num_features, logger, method='FAST'):
        self.max_num_features = max_num_features
        self.logger = logger
        self.method = method
        self.detector = None

        self.regular_grid_max_pts = None

        if self.method == 'FAST':
            self.detector = cv2.FastFeatureDetector_create(threshold=FAST_THRESHOLD, nonmaxSuppression=True)
        elif self.method == 'ORB':
            self.detector = cv2.ORB_create(nfeatures=max_num_features)
        elif self.method == 'SIFT':
            self.detector = cv2.xfeatures2d.SIFT_create(max_num_features)
        elif self.method == 'SURF':
            self.detector = cv2.xfeatures2d.SURF_create(max_num_features)
        elif self.method == 'SHI-TOMASI':
            self.detector = None
        elif self.method == 'REGULAR_GRID':
            self.regular_grid_max_pts = max_num_features
        else:
            self.logger.warn(method + "detector is not available")

    def detect(self, img: np.array):
        keypoints = None
        descriptors = None

        if self.method == 'SHI-TOMASI':
            keypoints = cv2.goodFeaturesToTrack(img, **shi_tomasi_params)
        elif self.method == 'ORB':
            keypoints = self.detector.detect(img, None)
            keypoints, descriptors = self.detector.compute(img, keypoints)
        elif self.method == 'FAST':
            keypoints = self.detector.detect(img, None)
        elif self.method == 'REGULAR_GRID':
            keypoints = self.regular_grid_detector(img)
        else:
            keypoints, descriptors = self.detector.detectAndCompute(img, None)


        self.logger.debug(f"Found {len(keypoints)} feautures")
        if not self.method == 'SHI-TOMASI':
            keypoints = np.array([x.pt for x in keypoints], dtype=np.float32).reshape((-1, 2))
        return (keypoints, descriptors)

    def regular_grid_detector(self, img):
        """
        Very basic method of just sampling point from a regular grid
        """
        # Fix at 1000
        self.regular_grid_max_pts = 1000

        features = list()
        height = float(img.shape[0])
        width = float(img.shape[1])
        k = height/width

        n_col = int(np.sqrt(self.regular_grid_max_pts/k))
        n_rows = int(n_col*k)

        h_cols = int(width/n_col)
        h_rows = int(height/n_rows)

        Kp = namedtuple("Kp", "pt")

        for c in range(n_col):
            for r in range(n_rows):
                features.append(Kp(pt=(c*h_cols, r*h_rows)))

        return features