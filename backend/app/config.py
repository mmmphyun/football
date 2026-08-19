"""Central configuration for the backend."""

import os
from pathlib import Path

DATA_DIR = Path(os.environ.get("DATA_DIR", "./data"))
RAW_DIR = DATA_DIR / "raw"
DB_PATH = DATA_DIR / "db.sqlite"

# Competition selection overrides
COMPETITION_ID = os.environ.get("COMPETITION_ID")
SEASON_ID = os.environ.get("SEASON_ID")
MIN_MATCHES = int(os.environ.get("MIN_MATCHES", "30"))

# StatsBomb Open Data endpoints
SB_RAW_BASE = "https://raw.githubusercontent.com/statsbomb/open-data/master"
SB_API_BASE = "https://api.github.com/repos/statsbomb/open-data/contents"

# Pitch geometry (StatsBomb coordinates)
PITCH_W = 120.0
PITCH_H = 80.0

# Highlight window policy
GOAL_CAP_SECONDS = 30
SHOT_CAP_SECONDS = 15
AFTER_EVENT_SECONDS = 4
HIGHLIGHT_XG_THRESHOLD = 0.25
MAX_PERIOD = 4  # exclude penalty shootouts (period 5+)

# Movement / prediction
SPRINT_SPEED = 5.5  # m/s
MAX_SPEED_CAP = 8.0  # m/s
PREDICT_HORIZON = 2.0  # seconds
PREDICT_PULL = 0.15  # per-second pull weight toward anchor

# Transitions
TRANSITION_WINDOW_SECONDS = 8
TRANSITION_MAX_EVENTS = 4