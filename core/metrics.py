"""Performance + experimental-cost measurement."""
import threading
import time

from config import settings


class MetricsCollector:
    def __init__(self, cost_units=None, mode="parallel"):
        self.cost_units = cost_units or settings.COST_UNITS
        self.mode = mode
        self._lock = threading.Lock()
        self.agent_calls = 0
        self.tool_calls = 0
        self.retries = 0
        self.processing_ops = 0
        self.agent_times = {}      # label -> [seconds, ...]
        self.stage_times = []      # {"stage", "wall_s", "task_sum_s"}
        self._t0 = None
        self._t1 = None

    # ---- counters ---------------------------------------------------
    def start(self):
        self._t0 = time.perf_counter()

    def stop(self):
        self._t1 = time.perf_counter()

    def count_agent_call(self):
        with self._lock:
            self.agent_calls += 1

    def count_tool_call(self):
        with self._lock:
            self.tool_calls += 1

    def count_retry(self):
        with self._lock:
            self.retries += 1

    def add_ops(self, n):
        with self._lock:
            self.processing_ops += int(n)

    def record_agent_time(self, label, seconds):
        with self._lock:
            self.agent_times.setdefault(label, []).append(seconds)

    def record_stage(self, name, wall_s, task_times):
        with self._lock:
            self.stage_times.append({"stage": name, "wall_s": wall_s, "task_sum_s": sum(task_times)})

    # ---- derived ----------------------------------------------------
    @property
    def total_time(self):
        end = self._t1 if self._t1 is not None else time.perf_counter()
        return (end - self._t0) if self._t0 is not None else 0.0

    @property
    def sequential_time(self):
        """Estimated time if every staged task ran one after another."""
        return sum(s["task_sum_s"] for s in self.stage_times)

    @property
    def parallel_time(self):
        """Actual wall-clock time spent inside the staged execution."""
        return sum(s["wall_s"] for s in self.stage_times)

    def speedup(self):
        return self.sequential_time / self.parallel_time if self.parallel_time > 0 else 1.0

    def cost(self):
        u = self.cost_units
        parts = {
            "agent_calls": self.agent_calls * u["agent_call"],
            "tool_calls": self.tool_calls * u["tool_call"],
            "retries": self.retries * u["retry"],
            "processing_ops": self.processing_ops * u["processing_op"],
        }
        parts["total"] = round(sum(parts.values()), 2)
        return {k: round(v, 2) for k, v in parts.items()}

    def summary(self):
        return {
            "mode": self.mode,
            "total_time_s": round(self.total_time, 4),
            "sequential_time_s": round(self.sequential_time, 4),
            "parallel_time_s": round(self.parallel_time, 4),
            "speedup": round(self.speedup(), 2),
            "agent_calls": self.agent_calls,
            "tool_calls": self.tool_calls,
            "retries": self.retries,
            "processing_ops": self.processing_ops,
            "cost": self.cost(),
            "agent_times_s": {k: [round(x, 4) for x in v] for k, v in self.agent_times.items()},
            "stage_times": [{k: (round(v, 4) if isinstance(v, float) else v) for k, v in s.items()}
                            for s in self.stage_times],
        }
