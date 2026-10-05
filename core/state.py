"""Shared workflow state: single source of truth with guarded, validated writes."""
import copy
import hashlib
import json
import threading
import time
import uuid

from core.exceptions import UnauthorizedStateWrite
from security.state_guard import StateGuard

DERIVED_KEYS = ("raw_search_results", "search_results", "filtered_results", "rejected_results",
                "comparison", "ranking", "validation", "conflicts", "human_approval",
                "final_recommendation")


class SharedWorkflowState:
    def __init__(self, user_query, workflow_id=None):
        self._lock = threading.RLock()
        self.workflow_id = workflow_id or uuid.uuid4().hex[:8]
        self.user_query = user_query
        self.clean_query = None
        self.requirements = {}
        self.plan = []
        self.routing = {}
        self.messages = []
        self.raw_search_results = {}
        self.search_results = []
        self.filtered_results = []
        self.rejected_results = []
        self.comparison = {}
        self.ranking = []
        self.validation = {}
        self.conflicts = []
        self.human_approval = {}
        self.final_recommendation = {}
        self.errors = []
        self.trace = []
        self.metrics = {}
        self.status = "created"
        self.security_events = []
        self._locked = set()
        self._req_hash = None

    # ---- guarded writes ---------------------------------------------
    def _check(self, writer, key):
        try:
            StateGuard.check_write(writer, key, self._locked)
        except UnauthorizedStateWrite as exc:
            self.record_security_event("unauthorized_state_write", writer=writer, key=key, detail=str(exc))
            raise

    def update(self, writer, key, value):
        with self._lock:
            self._check(writer, key)
            setattr(self, key, copy.deepcopy(value))

    def put_item(self, writer, key, subkey, value):
        with self._lock:
            self._check(writer, key)
            getattr(self, key)[subkey] = copy.deepcopy(value)

    def append(self, writer, key, value):
        with self._lock:
            self._check(writer, key)
            getattr(self, key).append(copy.deepcopy(value))

    # ---- requirement protection ---------------------------------------
    @staticmethod
    def _hash(req):
        return hashlib.sha256(json.dumps(req, sort_keys=True, default=str).encode()).hexdigest()

    def lock_requirements(self, writer):
        with self._lock:
            if writer not in ("planner", "orchestrator"):
                self.record_security_event("unauthorized_lock", writer=writer)
                raise UnauthorizedStateWrite(f"'{writer}' may not lock requirements")
            self._req_hash = self._hash(self.requirements)
            self._locked.add("requirements")

    def verify_requirements_integrity(self):
        """False if requirements were never locked or were changed after locking."""
        with self._lock:
            return self._req_hash is not None and self._hash(self.requirements) == self._req_hash

    # ---- misc -----------------------------------------------------------
    def record_security_event(self, event_type, **details):
        with self._lock:
            self.security_events.append({"ts": time.time(), "event": event_type, **details})

    def reset_derived(self):
        """Clear derived results before a human-requested re-analysis (requirements stay locked)."""
        with self._lock:
            fresh = SharedWorkflowState("")
            for key in DERIVED_KEYS:
                setattr(self, key, getattr(fresh, key))

    def snapshot(self):
        with self._lock:
            return copy.deepcopy({k: v for k, v in self.__dict__.items() if not k.startswith("_")})
