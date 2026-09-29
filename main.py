#!/usr/bin/env python3
"""
NewsLens — AI-Powered News Intelligence CLI
Usage: python main.py
"""

import sys
import os
from core.cli import run_cli

if __name__ == "__main__":
    try:
        run_cli()
    except KeyboardInterrupt:
        print("\n\n[Exited NewsLens]")
        sys.exit(0)
