from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List


@dataclass(slots=True)
class ProjectRecord:
    name: str
    path: Path
    archived: bool = False


@dataclass(slots=True)
class Registry:
    active_project: str | None = None
    projects: Dict[str, ProjectRecord] = field(default_factory=dict)


@dataclass(slots=True)
class ProjectIndex:
    project: str
    generated_at: str
    root: str
    file_count: int
    extension_stats: Dict[str, int]
    files: List[dict]


@dataclass(slots=True)
class CompletionContract:
    required_file_exists: List[str] = field(default_factory=list)
    required_text_contains: Dict[str, str] = field(default_factory=dict)
    require_shell_exit_zero: bool = False
    # Optional: reported shell working directory (for diagnosing filesystem vs shell root mismatch).
    shell_cwd: str | None = None
    # Optional: absolute path the shell used (e.g. from error message) to compare with project file.
    shell_target_path: str | None = None


@dataclass(slots=True)
class VerificationResult:
    passed: bool
    evidence: List[str] = field(default_factory=list)
    reasons: List[str] = field(default_factory=list)


@dataclass(slots=True)
class TaskOutcome:
    status: str
    evidence: List[str] = field(default_factory=list)
    reason: str = ""


@dataclass(slots=True)
class ExecutionGuardState:
    step_index: int = 1
    max_steps: int = 20
    action_fingerprint: str = ""
    previous_action_fingerprint: str = ""
    repeated_fingerprint_count: int = 0
    max_repeated_fingerprint: int = 2
    no_progress_steps: int = 0
    max_no_progress_steps: int = 3
