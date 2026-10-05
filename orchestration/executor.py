"""Sequential vs parallel execution of a stage's jobs (times every job)."""
import time
from concurrent.futures import ThreadPoolExecutor


def _timed(fn):
    t0 = time.perf_counter()
    result = fn()
    return result, time.perf_counter() - t0


def run_tasks(jobs, parallel=True, max_workers=8):
    """jobs: list of (task_id, zero-arg callable). Returns {task_id: (result, seconds)}.
    Only independent tasks of the same stage are ever passed in together."""
    results = {}
    if parallel and len(jobs) > 1:
        with ThreadPoolExecutor(max_workers=min(max_workers, len(jobs)), thread_name_prefix="agent") as pool:
            futures = {tid: pool.submit(_timed, fn) for tid, fn in jobs}
            for tid, fut in futures.items():
                results[tid] = fut.result()
    else:
        for tid, fn in jobs:
            results[tid] = _timed(fn)
    return results
