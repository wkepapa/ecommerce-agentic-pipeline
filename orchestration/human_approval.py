"""Human-in-the-loop gate: approve / reject / re-analyse / review reasoning / flag wrong info."""
import time


class HumanApprovalGate:
    """mode: 'interactive' (asks in the terminal) | 'auto' (approve) | 'reject' | 'scripted'."""

    def __init__(self, mode="auto", decisions=None, input_fn=input, output_fn=print):
        self.mode = mode
        self.decisions = list(decisions or [])
        self.input_fn = input_fn
        self.output_fn = output_fn

    @staticmethod
    def _result(decision, comment, mode):
        return {"decision": decision, "comment": comment, "mode": mode, "timestamp": time.time()}

    def request(self, context):
        if self.mode == "auto":
            return self._result("approve", "auto-approved (non-interactive run)", self.mode)
        if self.mode == "reject":
            return self._result("reject", "auto-rejected (test mode)", self.mode)
        if self.mode == "scripted":
            decision = self.decisions.pop(0) if self.decisions else "approve"
            return self._result(decision, "scripted decision", self.mode)
        return self._interactive(context)

    # ---- interactive ---------------------------------------------------------------
    def _show(self, ctx):
        out = self.output_fn
        out("\n" + "=" * 70)
        out("HUMAN APPROVAL REQUIRED")
        out("=" * 70)
        out(f"Requirements : { {k: v for k, v in ctx['requirements'].items() if v is not None} }")
        out(f"Validation   : {ctx['validation']}")
        for reason in ctx["escalation_reasons"]:
            out(f"  ! {reason}")
        out("-" * 70)
        for p in ctx["ranking"]:
            out(f"#{p['rank']}  {p['name']:<28} ₹{p['price']:>8,.0f}  RAM {p['ram_gb']:>2}GB  "
                f"SSD {p['storage_gb']:>4}GB  rating {p['rating']}  score {p['score']}")

    def _interactive(self, ctx):
        self._show(ctx)
        prompt = "\n[A]pprove  [R]eject  [N]ew analysis  [V]iew reasoning  [F]lag wrong info > "
        while True:
            try:
                choice = self.input_fn(prompt).strip().lower()
            except (EOFError, KeyboardInterrupt):
                return self._result("reject", "no human input available", self.mode)
            if choice in ("a", "approve"):
                return self._result("approve", "approved by human", self.mode)
            if choice in ("r", "reject"):
                return self._result("reject", "rejected by human", self.mode)
            if choice in ("n", "new", "reanalyse"):
                return self._result("reanalyse", "human requested another analysis", self.mode)
            if choice in ("f", "flag"):
                note = self.input_fn("Describe the incorrect information > ").strip()
                return self._result("flag", note or "incorrect information flagged", self.mode)
            if choice in ("v", "view"):
                for p in ctx["ranking"]:
                    self.output_fn(f"- {p['reasoning']}")
                for c in ctx["conflicts"]:
                    self.output_fn(f"- conflict: {c['product']} {c['field']} {c['values']} "
                                   f"-> {c['resolved_value']} ({c['resolved_by']}, {c['severity']})")
                continue
            self.output_fn("Please type A, R, N, V or F.")
