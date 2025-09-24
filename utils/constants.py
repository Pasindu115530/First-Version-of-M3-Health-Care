"""
Constants for Safe Warner application
"""

# Eye landmarks (MediaPipe Face Mesh indices)
LEFT_EYE_LANDMARKS = [33, 160, 158, 133, 153, 144]
RIGHT_EYE_LANDMARKS = [362, 385, 387, 263, 373, 380]

# Pose landmarks
NOSE_TIP = 0
LEFT_SHOULDER = 11
RIGHT_SHOULDER = 12
LEFT_EAR = 7
RIGHT_EAR = 8

# Thresholds
EAR_THRESHOLD = 0.20
PROXIMITY_THRESHOLD = 0.35
POSTURE_TILT_THRESHOLD = 15
SLOUCH_THRESHOLD = 0.15
GAZE_THRESHOLD = 0.2

# Timing parameters (in seconds)
BLINK_WINDOW = 10
SCREEN_TIME_BREAK = 20 * 60  # 20 minutes
NOTIFICATION_COOLDOWN = 30
EYE_EXERCISE_DURATION = 15
# For testing, reduce auto-mode interval to 2 minutes
AUTO_MODE_INTERVAL = 30

# Color codes (BGR format for OpenCV)
COLORS = {
    'RED': (0, 0, 255),
    'GREEN': (0, 255, 0),
    'BLUE': (255, 0, 0),
    'YELLOW': (0, 255, 255),
    'ORANGE': (0, 165, 255),
    'MAGENTA': (255, 0, 255),
    'CYAN': (255, 255, 0),
    'WHITE': (255, 255, 255),
    'BLACK': (0, 0, 0)
}

# Alert type colors
ALERT_COLORS = {
    'proximity': COLORS['RED'],      # Red for proximity alerts
    'blink_rate': COLORS['ORANGE'],  # Orange for blink rate
    'screen_time': COLORS['CYAN'],   # Cyan for screen time
    'posture': COLORS['MAGENTA'],    # Magenta for posture
    'good': COLORS['GREEN'],         # Green for good status
    'gaze': COLORS['WHITE']          # White for gaze info
}