from argparse import ArgumentParser
import logging

from people_guidance.pipeline import Pipeline
from people_guidance.utils import init_logging

from people_guidance.modules.drivers_module import DriversModule
from people_guidance.modules.position_estimation_module import PositionEstimationModule

from people_guidance.modules.fps_logger_module import FPSLoggerModule
from people_guidance.modules.visualization_module import VisualizationModule
from people_guidance.modules.reprojection_module import ReprojectionModule
from people_guidance.modules.feature_tracking_module import FeatureTrackingModule


if __name__ == '__main__':
    init_logging()

    # Arguments for different hardware configuration cases
    parser = ArgumentParser()
    parser.add_argument('--record', '-c',
                        help='Path of folder where to record dataset to',
                        type=str,
                        default='')
    parser.add_argument('--replay', '-p',
                        help='Path of folder where to replay dataset from',
                        type=str,
                        default='')
    parser.add_argument('--deploy', '-d',
                        help='Deploy the pipeline on a raspberry pi.',
                        action='store_true')
    args = parser.parse_args()

    pipeline = Pipeline(args)

    pipeline.add_module(DriversModule, log_level=logging.INFO)
    # Handles hardware drivers and interfaces
    pipeline.add_module(FeatureTrackingModule,  log_level=logging.INFO)
    # Handles IMU data to compute a position estimation
    pipeline.add_module(ReprojectionModule)
    pipeline.add_module(PositionEstimationModule)
    pipeline.add_module(FPSLoggerModule)
    pipeline.add_module(VisualizationModule)


    pipeline.start()
