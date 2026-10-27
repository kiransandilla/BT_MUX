# server/src/demo_config.py

# ==============================================================================
# BLE Scanning Configuration
# ==============================================================================
TARGET_DEVICE_PREFIX = "BTv2_"
SCAN_WAIT_TIME_SEC = 5

# ==============================================================================
# Execution & Timeout Configuration
# ==============================================================================
DEGRADED_TIMEOUT_MS = 4000
T_SLICE_MS = 2000
MAX_LOOP_WAIT_SEC_PER_CHUNK = 1
LOOP_WAIT_STEP = 0.1
SESSION_MGR_FLUSH_PUMP_THROTTLE_SECONDS = 0.1
BLEAK_CLIENT_CONNECT_TIMEOUT_SEC = 2
BLEAK_CLIENT_DISCONNECT_TIMOUT_SEC = 2

# Fix 1: Non-negotiable TDM guard band between disconnect() and connect()
TDM_GUARD_BAND_MS = 200
GUARD_BAND_FLOOR_MS = 150
GUARD_BAND_CEILING_MS = 300

# Fix 3: Per-device cooldown to accommodate slow Android BLE state-machine resets.
# Prevents the scheduler from hammering a peripheral immediately after a disconnect.
PERIPHERAL_COOLDOWN_MS = 3000

# ==============================================================================
# Payload Configuration
# ==============================================================================
FILE_CHUNK_SIZE_BYTES = 20
DEFAULT_TEXT_PAYLOAD_TEMPLATE = "VIVA_{node_id}_{seq}"