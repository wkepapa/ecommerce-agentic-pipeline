"""Search tool: reads one product source (simulated latency + fault injection)."""
import json
import threading
import time

from config import settings
from core.exceptions import PermanentToolError, TransientToolError


class FaultInjector:
    """Make a source fail N times with a recoverable error (used for failure testing)."""

    def __init__(self, faults=None):
        self._faults = dict(faults or {})
        self._lock = threading.Lock()

    def configure(self, faults):
        with self._lock:
            self._faults.update(faults)

    def maybe_fail(self, source):
        with self._lock:
            remaining = self._faults.get(source, 0)
            if remaining > 0:
                self._faults[source] = remaining - 1
                raise TransientToolError(f"Simulated transient failure from {source}")


def make_search_tool(fault_injector, latency):
    def search_products(source, category=None):
        time.sleep(latency)                       # simulated network / DB latency
        fault_injector.maybe_fail(source)
        path = settings.DATA_DIR / f"products_{source}.json"
        if not path.exists():
            raise PermanentToolError(f"Unknown product source '{source}'")
        records = json.loads(path.read_text(encoding="utf-8"))
        if category:
            records = [r for r in records if str(r.get("category", "")).lower() == category]
        for r in records:
            r["source"] = source
        return {"data": records, "ops": len(records)}
    return search_products
