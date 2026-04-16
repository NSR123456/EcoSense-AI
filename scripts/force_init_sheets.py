import os
import sys
from dotenv import load_dotenv

# Add project root to sys.path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.services.google_sheets import DatabaseManager

def force_reinit():
    load_dotenv()
    db = DatabaseManager()
    
    print("Force-initializing Google Sheet structure...")
    
    # 1. Initialize tabs if missing
    db.initialize_workspace()
    
    # 2. Clear all tabs and force-write headers
    tabs = ["Active_Stream", "Campus_Schedule", "Audit_Ledger"]
    for tab in tabs:
        print(f"Cleaning and force-syncing headers for {tab}...")
        db.clear_tab(tab)
    
    # 3. Seed Campus_Schedule
    print("Seeding Campus_Schedule...")
    db.seed_campus_schedule()
    
    print("\n✅ Google Sheet is now ready with all columns and seed data!")

if __name__ == "__main__":
    force_reinit()
