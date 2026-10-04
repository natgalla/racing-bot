"""Shared file utilities for cache modules."""
import json
import logging
import os
import tempfile

logger = logging.getLogger(__name__)


def atomic_write_json(path: str, data) -> None:
    """Write JSON to a temp file in the same directory then atomically replace.

    This ensures a concurrent read never sees a truncated or partial JSON payload.
    On error the temp file is cleaned up and the failure is logged.
    """
    tmp_path = None
    try:
        cache_dir = os.path.dirname(path)
        with tempfile.NamedTemporaryFile(
            mode="w", dir=cache_dir, delete=False, suffix=".tmp"
        ) as tmp:
            tmp_path = tmp.name
            json.dump(data, tmp, indent=2)
        os.replace(tmp_path, path)
    except Exception:
        logger.exception("atomic_write_json: failed to save %s", path)
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError as exc:
                logger.debug("atomic_write_json: failed to unlink temp file: %s", exc)
