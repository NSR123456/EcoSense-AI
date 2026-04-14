"""Project paths for dashboard and pages."""

import os

_DASH = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(_DASH)

METADATA_PATH = os.path.join(ROOT, "data", "sample", "building_metadata.csv")
ENERGY_CSV_PATH = os.path.join(ROOT, "data", "sample", "building_energy.csv")
USERS_PATH = os.path.join(ROOT, "data", "sample", "users.csv")
