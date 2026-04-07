from __future__ import annotations

from local_ai_dev.domain.models import ExecutionGuardState


def check_execution_guard(guard: ExecutionGuardState) -> str:
    if guard.step_index > guard.max_steps:
        return f"guard:max_steps_exceeded:{guard.step_index}>{guard.max_steps}"

    if (
        guard.action_fingerprint
        and guard.previous_action_fingerprint
        and guard.action_fingerprint == guard.previous_action_fingerprint
        and guard.repeated_fingerprint_count >= guard.max_repeated_fingerprint
    ):
        return (
            "guard:repeated_action_fingerprint:"
            f"{guard.repeated_fingerprint_count}>={guard.max_repeated_fingerprint}"
        )

    if guard.no_progress_steps >= guard.max_no_progress_steps:
        return (
            "guard:no_progress_steps_exceeded:"
            f"{guard.no_progress_steps}>={guard.max_no_progress_steps}"
        )

    return ""
