#!/usr/bin/env python3
"""Entry point for running pyenvsearch as a module with python -m pyenvsearch."""

import sys

from .main import main

if __name__ == "__main__":
    sys.exit(main())
