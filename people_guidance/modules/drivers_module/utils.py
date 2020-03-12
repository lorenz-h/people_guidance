# MPU 6050 Registers,
# datasheet https://invensense.tdk.com/wp-content/uploads/2015/02/MPU-6000-Register-Map1.pdf

# FLAGS
DO_CALIB = False

# Device address
ADDR = 0x68

ACCEL_CONFIG = 0x17

GYRO_CONFIG = 0x18

ACCEL_XOUT_H_REG = 0x3B
ACCEL_XOUT_L_REG = 0x3C

ACCEL_YOUT_H_REG = 0x3D
ACCEL_YOUT_L_REG = 0x3E

ACCEL_ZOUT_H_REG = 0x3F
ACCEL_ZOUT_L_REG = 0x40

GYRO_XOUT_H_REG = 0x43
GYRO_XOUT_L_REG = 0x44

GYRO_YOUT_H_REG = 0x45
GYRO_YOUT_L_REG = 0x46

GYRO_ZOUT_H_REG = 0x47
GYRO_ZOUT_L_REG = 0x48

PWR_MGMT_1 = 0x6b
PWR_MGMT_2 = 0x6c

# Earth acceleration in Zurich
ACCEL_G = 9.80600

# Accel full range in m/s^2
ACCEL_RANGE = 2.0*ACCEL_G

# 16 signed, max val
IMU_MAX_VAL = 32768

# Gyro full range in °/s
GYRO_RANGE = 250

# Coeffs
ACCEL_COEFF = ACCEL_RANGE/IMU_MAX_VAL
GYRO_COEFF = GYRO_RANGE/IMU_MAX_VAL

#Calibrations values
ACCEL_CALIB_X = 0
ACCEL_CALIB_Y = 0
ACCEL_CALIB_Z = 0

GYRO_CALIB_X = 0
GYRO_CALIB_Y = 0
GYRO_CALIB_Z = 0
