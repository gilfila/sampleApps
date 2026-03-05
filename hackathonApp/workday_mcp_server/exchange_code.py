#!/usr/bin/env python3
"""
One-time script to exchange an authorization code for access_token and refresh_token.

PKCE flow (recommended):
  1. python exchange_code.py --url-pkce   # Prints authorize URL, saves code_verifier
  2. Open the URL, sign in, copy the code=... from the redirect
  3. python exchange_code.py <code>       # Uses saved code_verifier, prints WORKDAY_REFRESH_TOKEN

Without PKCE:
  1. python exchange_code.py --url        # Prints authorize URL
  2. Open URL, sign in, copy code from redirect
  3. python exchange_code.py <code>

Then add the printed WORKDAY_REFRESH_TOKEN_NONEXPIRE=... to your .env file.
"""

import os
import sys

# Load .env from script directory
_load_dir = os.path.dirname(os.path.abspath(__file__))
if _load_dir not in sys.path:
    sys.path.insert(0, _load_dir)

from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(_load_dir, ".env"))

from workday_auth import (
    exchange_authorization_code,
    get_workday_authorize_url,
    get_workday_authorize_url_pkce,
)

PKCE_VERIFIER_FILE = os.path.join(_load_dir, ".workday_pkce_verifier")


def main() -> None:
    if len(sys.argv) > 1:
        arg = sys.argv[1].strip()
    else:
        arg = sys.stdin.read().strip() if not sys.stdin.isatty() else ""

    if arg == "--url":
        print(get_workday_authorize_url(response_type="code"))
        return

    if arg == "--url-pkce":
        url, verifier = get_workday_authorize_url_pkce()
        try:
            with open(PKCE_VERIFIER_FILE, "w") as f:
                f.write(verifier)
        except OSError as e:
            print(f"Warning: could not save code_verifier: {e}", file=sys.stderr)
            print("Use this code_verifier when exchanging:", verifier, file=sys.stderr)
        print("Open this URL, sign in, then run: python exchange_code.py <code>")
        print()
        print(url)
        return

    code = arg
    if not code:
        print("Usage: python exchange_code.py <authorization_code>", file=sys.stderr)
        print("  python exchange_code.py --url       # Authorize URL (no PKCE)", file=sys.stderr)
        print("  python exchange_code.py --url-pkce  # Authorize URL with PKCE (recommended)", file=sys.stderr)
        sys.exit(1)

    code_verifier = None
    if os.path.isfile(PKCE_VERIFIER_FILE):
        try:
            with open(PKCE_VERIFIER_FILE) as f:
                code_verifier = f.read().strip()
            os.remove(PKCE_VERIFIER_FILE)
        except OSError:
            pass

    try:
        data = exchange_authorization_code(code, code_verifier=code_verifier)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    print("Add this to your .env file:\n")
    if data.get("refresh_token"):
        print(f"WORKDAY_REFRESH_TOKEN_NONEXPIRE={data['refresh_token']}")
    print()


if __name__ == "__main__":
    main()
