import numpy as np

# Debug mode
DEBUG_POSITION = 0  # 0: none, 1: light, 2: mid, 3: extended, 4: full debug options

# Queue output
POS_VALIDITY_MS = 100
POSITION_PUBLISH_FREQ = 1
POSITION_PUBLISH_ACC_FREQ = 0
POSITION_PUBLISH_INPUT_FREQ = 0

# Reduce the velocity to reduce drift
METHOD_RESET_VELOCITY = True
RESET_VEL_FREQ = 200 # select value above 100 to compensate after each step  TODO : prone to dt
RESET_VEL_FREQ_COEF_X = 0.991
RESET_VEL_FREQ_COEF_Y = 0.991
RESET_VEL_FREQ_COEF_Z = 0.97

# Error calculation
MEASURE_SUMMED_ERROR_ACC = False
METHOD_ERROR_ACC_CORRECTION = True # worse otherwise
PUBLISH_SUMMED_MEASURE_ERROR_ACC = 4

# dataset_1
SUM_DT_DATASET_1 = 9.622
SUM_ELT_DATASET_1 = 2751
SUM_ACC_DATASET_1 = [-42.77572310263783, -170.8575616629757, -1633.801397779215]

if METHOD_ERROR_ACC_CORRECTION:
    CORRECTION_ACC = np.divide(SUM_ACC_DATASET_1, SUM_ELT_DATASET_1)
else:
    CORRECTION_ACC = [0, 0, 0]

# Time calculation to get an output in seconds
DIVIDER_OUTPUTS_SECONDS = 1000000000
DIVIDER_OUTPUTS_mSECONDS = 1000

# Complementary filter parameter
ALPHA_COMPLEMENTARY_FILTER = 0.02
