#!/usr/bin/env python3
import sys
sys.path.insert(0, r"d:\EcoSense LG")

try:
    import dashboard.app
    print("Dashboard import successful")
except Exception as e:
    print(f"Import failed: {e}")
    import traceback
    traceback.print_exc()