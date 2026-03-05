#!/usr/bin/env python3
"""
Quick test for get_worker_profile tool.
Run from workday_mcp_server: python test_get_worker_profile.py [employee_id]
Default employee_id is "1" (Employee_ID type) if not provided.
"""
import os
import sys

# Run from this package directory so .env and imports resolve
os.chdir(os.path.dirname(os.path.abspath(__file__)))
if os.getcwd() not in sys.path:
    sys.path.insert(0, os.getcwd())

from server import get_worker_profile

def main():
    employee_id = sys.argv[1] if len(sys.argv) > 1 else "1"
    print(f"Calling get_worker_profile(employee_id={employee_id!r})...")
    result = get_worker_profile(employee_id)
    print(result)

if __name__ == "__main__":
    main()
