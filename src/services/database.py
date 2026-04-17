"""Database abstraction for the EcoSense AI energy audit framework."""

from src.services.google_sheets import DatabaseManager

# Alias for the underlying Google Sheets database manager.
# This layer exists to keep the MAS components modular and to support
# a future replacement of the persistence backend without changing the agents.

class SpreadsheetDatabase(DatabaseManager):
    pass

# Expose the original manager name for compatibility.
DatabaseManager = SpreadsheetDatabase
