"""Controlled retry: only recoverable errors, bounded attempts, small backoff."""
import time

from config import settings
from core.exceptions import WorkflowError


def run_with_retry(fn, max_retries, on_retry=None):
    """Run fn(). Returns (result, retries_used). Raises the last error with `.attempts` set."""
    attempt = 0
    while True:
        try:
            return fn(), attempt
        except WorkflowError as exc:
            if not exc.recoverable or attempt >= max_retries:
                exc.attempts = attempt
                raise
            attempt += 1
            if on_retry:
                on_retry(attempt, exc)
            time.sleep(settings.RETRY_BACKOFF * attempt)
