from __future__ import annotations

from pathlib import Path

from local_ai_dev.domain.models import CompletionContract, VerificationResult


def verify_completion_contract(
    *,
    project_root: Path,
    contract: CompletionContract,
    shell_exit_code: int | None = None,
) -> VerificationResult:
    evidence: list[str] = []
    reasons: list[str] = []
    filesystem_ok = True

    for rel_path in contract.required_file_exists:
        target = (project_root / rel_path).resolve()
        if target.is_file():
            evidence.append(f"file_exists:{rel_path}")
        else:
            reasons.append(f"missing_file:{rel_path}")
            filesystem_ok = False

    for rel_path, expected_text in contract.required_text_contains.items():
        target = (project_root / rel_path).resolve()
        if not target.is_file():
            reasons.append(f"missing_file_for_text_check:{rel_path}")
            filesystem_ok = False
            continue
        content = target.read_text(encoding="utf-8", errors="replace")
        if expected_text in content:
            evidence.append(f"text_contains:{rel_path}")
        else:
            reasons.append(f"text_not_found:{rel_path}")
            filesystem_ok = False

    if contract.require_shell_exit_zero:
        if shell_exit_code == 0:
            evidence.append("shell_exit_code:0")
        elif shell_exit_code is None:
            reasons.append("shell_exit_code_missing")
        else:
            reasons.append(f"shell_exit_code_not_zero:{shell_exit_code}")

    if (
        contract.require_shell_exit_zero
        and shell_exit_code is not None
        and shell_exit_code != 0
        and filesystem_ok
    ):
        _append_shell_filesystem_mismatch_reasons(
            project_root=project_root,
            contract=contract,
            reasons=reasons,
        )

    return VerificationResult(
        passed=len(reasons) == 0,
        evidence=evidence,
        reasons=reasons,
    )


def _append_shell_filesystem_mismatch_reasons(
    *,
    project_root: Path,
    contract: CompletionContract,
    reasons: list[str],
) -> None:
    """When filesystem checks passed but shell failed, diagnose cwd/path mismatch."""
    root_resolved = project_root.resolve()
    if contract.shell_cwd:
        try:
            cwd_resolved = Path(contract.shell_cwd).resolve()
        except OSError:
            reasons.append("environment_mismatch:shell_cwd_unresolvable")
            return
        if cwd_resolved != root_resolved:
            reasons.append(
                "environment_mismatch:shell_cwd_differs_from_project_root"
                f":shell_cwd={cwd_resolved.as_posix()}"
                f":project_root={root_resolved.as_posix()}"
            )

    if contract.shell_target_path and contract.required_file_exists:
        rel0 = contract.required_file_exists[0]
        expected = (project_root / rel0).resolve()
        try:
            shell_path = Path(contract.shell_target_path).resolve()
        except OSError:
            reasons.append("environment_mismatch:shell_target_path_unresolvable")
            return
        if shell_path != expected:
            reasons.append(
                "environment_mismatch:shell_target_path_differs_from_project_file"
                f":shell_target={shell_path.as_posix()}"
                f":expected={expected.as_posix()}"
            )

    if not contract.shell_cwd and not contract.shell_target_path:
        reasons.append(
            "environment_mismatch:shell_failed_while_filesystem_ok"
            "; pass --shell-cwd or --shell-target-path to diagnose cwd vs project root"
        )
