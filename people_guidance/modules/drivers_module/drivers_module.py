import io
import smbus

from picamera import mmal, mmalobj
from pathlib import Path
from time import sleep, monotonic
from queue import Queue

from ..module import Module
from .utils import *


class DriversModule(Module):
    def __init__(self, log_dir: Path, args=None):
        super(DriversModule, self).__init__(name="drivers_module", outputs=[("images", 10), ("accelerations", 100)],
                                            input_topics=[], log_dir=log_dir)
        self.args = args

    def start(self):
        self.logger.info("Starting drivers")

        # General inits
        self.files_dir = None
        self.imu_data = None
        self.img_data = None
        self.img_counter = 0
        self.RECORD_MODE = False
        self.REPLAY_MODE = False

        # CAMERA INITS
        self.camera = mmalobj.MMALCamera()
        self.encoder = mmalobj.MMALImageEncoder()
        self.q_img = Queue()

        # IMU INITS
        self.bus = smbus.SMBus(1)
        self.imu_next_sample_ms = self.get_time_ms()

        # CAMERA SETUP
        self.camera_pipeline_setup()
        self.camera_start()

        # IMU SETUP
        self.bus.write_byte_data(ADDR, PWR_MGMT_1, 0)
        self.set_accel_range()
        self.set_gyro_range()

        # TODO: handle calibration case

        # Get hardware configuration mode
        self.setup_hardware_configuration()

        while(True):
            if self.REPLAY_MODE:
                pass
            else:
                if self.get_time_ms() > self.imu_next_sample_ms:
                    timestamp = self.get_time_ms()
                    self.imu_next_sample_ms = timestamp + IMU_SAMPLE_TIME_MS
                    data_dict = {'accel_x': self.get_accel_x(),
                                 'accel_y': self.get_accel_y(),
                                 'accel_z': self.get_accel_z(),
                                 'gyro_x': self.get_gyro_x(),
                                 'gyro_y': self.get_gyro_y(),
                                 'gyro_z': self.get_gyro_z()
                                 }
                    if self.RECORD_MODE:
                        self.imu_data.write(f"{timestamp}: ")
                        self.imu_data.write(f"accel_x: {data_dict['accel_x']}, ")
                        self.imu_data.write(f"accel_y: {data_dict['accel_y']}, ")
                        self.imu_data.write(f"accel_z: {data_dict['accel_z']}, ")
                        self.imu_data.write(f"gyro_x: {data_dict['gyro_x']}, ")
                        self.imu_data.write(f"gyro_y: {data_dict['gyro_y']}, ")
                        self.imu_data.write(f"gyro_z: {data_dict['gyro_z']}\n")
                        self.imu_data.flush()
                    else:
                        self.publish("accelerations", data_dict,
                                     IMU_VALIDITY_MS, timestamp)

                # We want to forward image data as fast and often as possible
                if not self.q_img.empty():
                    print(self.q_img.qsize())
                    # Get next img from queue
                    data_dict = self.q_img.get()
                    data = data_dict['data']
                    timestamp = data_dict['timestamp']

                    if self.RECORD_MODE:
                        self.img_counter += 1
                        # Keep track of image counter and timestamp
                        self.img_data.write(f"{self.img_counter}: {timestamp}\n")
                        self.img_data.flush()

                        # Write image
                        img = (self.files_dir / 'imgs' / f"img_{self.img_counter:04d}.jpg")
                        img_f = io.open(img, 'wb')
                        img_f.write(data)
                        img_f.close()
                    else:
                        self.publish("images", data,
                                     IMAGES_VALIDITY_MS, timestamp)

    def camera_pipeline_setup(self):
        # Camera output setup
        self.camera.outputs[0].format = mmal.MMAL_ENCODING_RGB24
        self.camera.outputs[0].framesize = CAMERA_FRAMESIZE
        self.camera.outputs[0].framerate = CAMERA_FRAMERATE
        self.camera.outputs[0].commit()

        # Encoder input setup
        self.encoder.inputs[0].format = mmal.MMAL_ENCODING_RGB24
        self.encoder.inputs[0].framesize = CAMERA_FRAMESIZE
        self.encoder.inputs[0].commit()

        # Encoder output setup
        self.encoder.outputs[0].copy_from(self.encoder.inputs[0])
        self.encoder.outputs[0].format = mmal.MMAL_ENCODING_JPEG
        self.encoder.outputs[0].params[mmal.MMAL_PARAMETER_JPEG_Q_FACTOR] = CAMERA_JPEG_QUALITY
        self.encoder.outputs[0].commit()

        # Connect encoder input to camera output
        self.encoder.connect(self.camera.outputs[0])
        self.encoder.connection.enable()

    def image_callback(self, port, buf):
        # Is called in separate thread
        self.q_img.put({'data': buf.data,
                        'timestamp': self.get_time_ms()})
        return False

    def get_time_ms(self):
        # https://www.python.org/dev/peps/pep-0418/#time-monotonic
        return int(round(monotonic() * 1000))

    def camera_start(self):
        self.encoder.outputs[0].enable(self.image_callback)

    def camera_stop(self):
        self.encoder.connection.disable()

    def set_accel_range(self):
        # Get current config
        config = self.read_byte(ACCEL_CONFIG)
        # Datasheet chapter 4.4, set to +-2g range
        config &= ~(1 << 3)
        config &= ~(1 << 4)
        # Write back
        self.bus.write_byte_data(ADDR, ACCEL_CONFIG, config)

    def set_gyro_range(self):
        # Get current gyro config
        config = self.read_byte(GYRO_CONFIG)
        # Datasheet chapter 4.5, set to +-250°/s range
        config &= ~(1 << 3)
        config &= ~(1 << 4)
        # Write back
        self.bus.write_byte_data(ADDR, GYRO_CONFIG, config)

    def get_accel_x(self):
        return self.read_word_2c(ACCEL_XOUT_H_REG)*ACCEL_COEFF - ACCEL_CALIB_X

    def get_accel_y(self):
        return self.read_word_2c(ACCEL_YOUT_H_REG)*ACCEL_COEFF - ACCEL_CALIB_Y

    def get_accel_z(self):
        return self.read_word_2c(ACCEL_ZOUT_H_REG)*ACCEL_COEFF - ACCEL_CALIB_Z

    def get_gyro_x(self):
        return self.read_word_2c(GYRO_XOUT_H_REG)*GYRO_COEFF - GYRO_CALIB_X

    def get_gyro_y(self):
        return self.read_word_2c(GYRO_YOUT_H_REG)*GYRO_COEFF - GYRO_CALIB_Y

    def get_gyro_z(self):
        return self.read_word_2c(GYRO_ZOUT_H_REG)*GYRO_COEFF - GYRO_CALIB_Z

    def read_byte(self, reg):
        return self.bus.read_byte_data(ADDR, reg)

    def read_word(self, reg):
        h = self.bus.read_byte_data(ADDR, reg)
        l = self.bus.read_byte_data(ADDR, reg+1)
        value = (h << 8) + l
        return value

    def read_word_2c(self, reg):
        val = self.read_word(reg)
        if (val >= 0x8000):
            return -((65535 - val) + 1)
        else:
            return val

    def imu_calibration(self, samples=100):
        self.logger.warning("IMU Calibration is starting now")
        ACCEL_CALIB_X = 0.0
        ACCEL_CALIB_Y = 0.0
        ACCEL_CALIB_Z = 0.0

        GYRO_CALIB_X = 0.0
        GYRO_CALIB_Y = 0.0
        GYRO_CALIB_Z = 0.0
        self.logger.warning("Calibrating X-axis")
        sleep(5)
        for s in range(samples):
            ACCEL_CALIB_X += self.get_accel_x() - ACCEL_G
            GYRO_CALIB_X += self.get_gyro_x()
            sleep(0.01)
        self.logger.warning("Calibrating Y-axis")
        sleep(5)
        for s in range(samples):
            ACCEL_CALIB_Y += self.get_accel_y() - ACCEL_G
            GYRO_CALIB_Y += self.get_gyro_y()
            sleep(0.01)
        self.logger.warning("Calibrating Z-axis")
        sleep(5)
        for s in range(samples):
            ACCEL_CALIB_Z += self.get_accel_z() + ACCEL_G
            GYRO_CALIB_Z += self.get_gyro_z()
            sleep(0.01)

        ACCEL_CALIB_X /= samples
        ACCEL_CALIB_Y /= samples
        ACCEL_CALIB_Z /= samples
        GYRO_CALIB_X /= samples
        GYRO_CALIB_Y /= samples
        GYRO_CALIB_Z /= samples

        self.logger.warning("AX: {}, AY: {}, AZ: {}, GX: {}, GY: {}, GZ: {}".format(
            ACCEL_CALIB_X, ACCEL_CALIB_Y, ACCEL_CALIB_Z, GYRO_CALIB_X, GYRO_CALIB_Y, GYRO_CALIB_Z))

    def setup_hardware_configuration(self):
        # Cannot replay and record at the same time
        if self.args.replay and self.args.record:
            self.logger.error("Specified replay and record, exiting")
            exit()

        if self.args.replay:
            self.REPLAY_MODE = True
            self.files_dir = Path(self.args.replay)

        elif self.args.record:
            self.RECORD_MODE = True
            self.files_dir = Path(self.args.record)

            # IMU files
            self.imu_data = (self.files_dir / 'imu_data.txt').open(mode='w')

            # Camera files
            self.img_data = (self.files_dir / 'img_data.txt').open(mode='w')
            (self.files_dir / 'imgs').mkdir(parents=True, exist_ok=True)
