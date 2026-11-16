"""Restrict transport recovery to the frozen parent's actual HTTP boundary."""

import hashlib
import inspect
from pathlib import Path
from alpha_evolve.fidelity_live_recovery_v2 import RecoveringLiveMeter
from alpha_evolve.publication_llm import CohortOpenRouter as OriginalCohort
from alpha_evolve.openrouter_budget import atomic_json

SOURCE, START = inspect.getsourcelines(OriginalCohort.request)
HTTP_LINES = {
    START + i
    for i, line in enumerate(SOURCE)
    if "urllib.request.urlopen(" in line or "response = json.loads(result.read())" in line
}
if len(HTTP_LINES) != 2:
    raise RuntimeError("Frozen HTTP boundary changed; inspect before enabling recovery")


class HttpBoundaryRecoveringMeter(RecoveringLiveMeter):
    def record_failed_attempt(self, endpoint, payload, error):
        traceback = error.__traceback__
        boundary = None
        while traceback:
            frame = traceback.tb_frame
            if frame.f_code is OriginalCohort.request.__code__:
                if traceback.tb_lineno in HTTP_LINES and "response" not in frame.f_locals:
                    boundary = {
                        "request_hash": frame.f_locals["key"],
                        "parent_http_line": traceback.tb_lineno,
                        "error_type": type(error).__name__,
                        "complete_response_received": False,
                        "scope": "Exception propagated from urlopen/read before a complete response was assigned; cache/ledger/journal timeouts are not eligible.",
                    }
                break
            traceback = traceback.tb_next
        if boundary is None:
            raise RuntimeError("Non-HTTP or persistence failure; no automatic retry, reconcile instead") from error
        # The parent creates its event directory; keep this separate so its
        # refusal to overwrite a prior event remains intact.
        proof = Path(self.root) / "http_boundary_proofs" / boundary["request_hash"]
        proof.mkdir(parents=True, exist_ok=False)
        code = Path(__file__).read_bytes()
        boundary["guard_sha256"] = hashlib.sha256(code).hexdigest()
        (proof / "executed_guard.py").write_bytes(code)
        atomic_json(proof / "proof.json", boundary)
        return super().record_failed_attempt(endpoint, payload, error)
