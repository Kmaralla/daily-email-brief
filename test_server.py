#!/usr/bin/env python3
"""Quick test to verify Flask server is running."""

import requests
import sys

try:
    response = requests.get('http://localhost:5000/health', timeout=2)
    if response.status_code == 200:
        print("✅ Server is running!")
        print(f"Response: {response.json()}")
        sys.exit(0)
    else:
        print(f"❌ Server returned status {response.status_code}")
        sys.exit(1)
except requests.exceptions.ConnectionError:
    print("❌ Cannot connect to server. Is it running?")
    print("   Run: python main.py setup")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
