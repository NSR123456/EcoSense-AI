"""Project paths for dashboard and pages."""

import os

_DASH = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(_DASH)

SAMPLE_DATA_DIR = os.path.join(ROOT, "data", "sample")
ENERGY_CSV_PATH = os.getenv(
    "ENERGY_CSV_PATH",
    os.path.join(SAMPLE_DATA_DIR, "ecosense_train_hourly.csv"),
)
METADATA_PATH = os.getenv(
    "BUILDING_METADATA_PATH",
    os.path.join(SAMPLE_DATA_DIR, "ecosense_metadata.csv"),
)
USERS_PATH = os.path.join(SAMPLE_DATA_DIR, "users.csv")
