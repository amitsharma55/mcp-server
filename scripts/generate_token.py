#!/usr/bin/env python3
"""Generate an HS256 JWT token for authenticating with the MCP server.

Usage:
    python scripts/generate_token.py
    python scripts/generate_token.py --sub amit --days 30
"""

import argparse
import datetime
import os
import sys

import jwt


def main():
    parser = argparse.ArgumentParser(description="Generate a JWT token")
    parser.add_argument("--sub", default="amit", help="Subject claim (default: amit)")
    parser.add_argument("--days", type=int, default=30, help="Token validity in days (default: 30)")
    args = parser.parse_args()

    secret = os.environ.get("JWT_SECRET")
    if not secret:
        # Try loading from .env file
        env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("JWT_SECRET="):
                        secret = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break

    if not secret:
        print("Error: JWT_SECRET not set. Export it or add to .env file.", file=sys.stderr)
        sys.exit(1)

    payload = {
        "sub": args.sub,
        "iat": datetime.datetime.now(datetime.timezone.utc),
        "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=args.days),
    }

    token = jwt.encode(payload, secret, algorithm="HS256")
    print(token)


if __name__ == "__main__":
    main()
