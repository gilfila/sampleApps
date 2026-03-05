#!/usr/bin/env python3
"""Print the access token that would be used for Workday API calls. Useful for debugging auth."""

import os
import sys

_load_dir = os.path.dirname(os.path.abspath(__file__))
if _load_dir not in sys.path:
    sys.path.insert(0, _load_dir)

from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(_load_dir, ".env"))

from workday_auth import get_workday_bearer_token

if __name__ == "__main__":
    try:
        token = get_workday_bearer_token()
        print("Access token:", token)
    except Exception as e:
        print("Error:", e, file=sys.stderr)
        sys.exit(1)
