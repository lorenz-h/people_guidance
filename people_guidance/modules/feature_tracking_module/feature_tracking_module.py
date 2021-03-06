import pathlib
import cv2
import numpy as np
import platform

from time import sleep
from scipy.spatial.transform import Rotation
from typing import Tuple

from people_guidance.modules.module import Module
from people_guidance.utils import project_path

from .config import *

from .matcher import bruteForceMatcher, opticalFlowMatcher

# Need this to get cv imshow working on Ubuntu 20.04
if "Linux" in platform.system():
    import gi
    gi.require_version('Gtk', '2.0')
    import matplotlib
    matplotlib.use('TkAgg')


class FeatureTrackingModule(Module):

    def __init__(self, log_dir: pathlib.Path, args=None):
        super(FeatureTrackingModule, self).__init__(name="feature_tracking_module", outputs=[("feature_point_pairs", 1000), ("feature_point_pairs_vis", 1000)],
                                                    inputs=["drivers_module:images"],
                                                    log_dir=log_dir)

    def start(self):
        self.fm = None
        if USE_OPTICAL_FLOW:
            self.fm = opticalFlowMatcher(OF_MAX_NUM_FEATURES, self.logger, self.intrinsic_matrix, self.distortion_coeffs, method=DETECTOR, use_H=USE_H, use_E=USE_E)
        else:
            self.fm = bruteForceMatcher(OF_MAX_NUM_FEATURES, self.logger, self.intrinsic_matrix, method=DETECTOR, use_H=USE_H, use_E=USE_E)

        self.old_timestamp = 0

        # Create a contrast limited adaptive histogram equalization filter
        clahe = cv2.createCLAHE(clipLimit=5.0)

        while True:
            img_dict = self.get("drivers_module:images")

            if not img_dict:
                self.logger.info("queue was empty")
            else:
                # extract the image data and time stamp
                img_rgb = img_dict["data"]["data"]
                timestamp = img_dict["data"]["timestamp"]

                self.logger.debug(f"Processing image with timestamp {timestamp} ...")

                img = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)

                # Apply clahe
                if USE_CLAHE:
                    img = clahe.apply(img)

                # Gaussian filter
                if USE_GAUSSIAN:
                    img = cv2.blur(img,(5,5))

                if self.fm.should_initialize:
                    self.fm.initialize(img)
                else:
                    mp1, mp2 = self.fm.match(img)
                    if mp1.shape[0] > 0:
                        inliers = (mp1, mp2)

                        transformations = self.fm.getTransformations()

                        if mp1.shape[0] > 0:
                            self.publish("feature_point_pairs",
                                        {"camera_positions" : transformations,
                                        "image": img_rgb,
                                        "point_pairs": inliers,
                                        "timestamp_pair": (self.old_timestamp, timestamp)},
                                        -1)
                            self.publish("feature_point_pairs_vis",
                                            {"point_pairs": inliers,
                                            "img": img_rgb,
                                            "timestamp": timestamp},
                                            -1)
                        self.old_timestamp = timestamp
