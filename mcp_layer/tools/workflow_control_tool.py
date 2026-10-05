"""Workflow-control capability used only by the Supervisor Agent."""


def assess_workflow(statuses, validation, conflicts):
    failed = [s for s in statuses if s["status"] != "success"]
    validation_ok = bool(validation) and all(v["passed"] for v in validation.values())
    high = [c for c in conflicts if c.get("severity") == "high"]
    reasons = []
    if failed:
        reasons.append(f"{len(failed)} agent task(s) failed or ran degraded: "
                       + ", ".join(f"{f['sender']}:{f['task']}" for f in failed))
    if not validation_ok:
        reasons.append("one or more validation checkpoints did not pass")
    if high:
        reasons.append(f"{len(high)} high-severity data conflict(s) resolved by trusted-source priority")
    return {"data": {"agents_ok": not failed, "failed_tasks": failed, "validation_ok": validation_ok,
                     "high_severity_conflicts": len(high), "escalation_reasons": reasons},
            "ops": len(statuses)}
