#!/usr/bin/env python3
"""Standalone cache refresh script — safe to run from cron."""
import logging
import sys
import os

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

sys.path.insert(0, os.path.dirname(__file__))

from tools.gtdb_cache import force_refresh_list

if __name__ == "__main__":
    force_refresh_list()
