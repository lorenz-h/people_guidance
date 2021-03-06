import pathlib
import logging
import os
from typing import Dict, List, Union

import numpy as np

import coloredlogs

ROOT_DIR = pathlib.Path(__file__).parent.parent
ROOT_LOG_DIR = ROOT_DIR / "logs"
ROOT_DATA_DIR = ROOT_DIR / "data"
#DEFAULT_DATASET = ROOT_DATA_DIR / "converted_eth_slam_large_loop_1"
#DEFAULT_DATASET = ROOT_DATA_DIR / "indoor_dataset_6"
DEFAULT_DATASET = ROOT_DATA_DIR / "outdoor_dataset_17_old"

if "converted_eth_slam" in DEFAULT_DATASET.stem and (DEFAULT_DATASET / "calibration.txt").exists():
    with open(DEFAULT_DATASET / "calibration.txt") as fp:
        line = fp.readline().replace("\n", "").replace("\r", "")
        fx, fy, cx, cy = (float(param) for param in line.split(" "))

    INTRINSIC_MATRIX = np.array([[fx, 0.0, cx], [0.0, fy, cy], [0.0, 0.0, 1.0]])
else:
    INTRINSIC_MATRIX = np.array([[644.90127548, 0.0, 406.99519054], [0.0, 644.99811417, 307.06244081], [0.0, 0.0, 1.0]])

DISTORTION_COEFFS = np.array([[ 0.19956839 , -0.49217089, -0.00235192, -0.00051292, 0.28251577]])


def project_path(relative_path: str) -> pathlib.Path:
    return ROOT_DIR / relative_path


def init_logging() -> None:
    logging.basicConfig(level=logging.DEBUG)


def get_logger(name: str, log_dir: pathlib.Path, level=logging.DEBUG):
    logger = logging.getLogger(name)
    logfile = log_dir / f"{name}_{os.getpid()}.log"

    coloredlogs.install(logger=logger, level=level)

    fh = logging.FileHandler(str(logfile))
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    return logger


def normalize(v: np.array) -> np.array:
    # normalizes a vector
    norm = np.linalg.norm(v)
    if norm == 0:
        return v
    else:
        return v / norm


class MovingAverageFilter:
    def __init__(self):
        self.keys: Dict[str, List] = {}

    def __call__(self, key: str, value: Union[int, float], window_size: int = 5):
        if key not in self.keys:
            self.keys[key] = [value]
        else:
            self.keys[key].append(value)
            while len(self.keys[key]) > window_size:
                self.keys[key].pop(0)

        return float(sum(self.keys[key]) / len(self.keys[key]))
