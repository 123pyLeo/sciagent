"""Environment snapshot helpers."""

from __future__ import annotations

import os
import platform
import subprocess
from pathlib import Path
from typing import Dict


def collect_environment_snapshot(workdir: Path) -> Dict[str, str]:
    snapshot: Dict[str, str] = {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "shell": os.environ.get("SHELL", ""),
    }
    git_info = _git_describe(workdir)
    if git_info:
        snapshot.update(git_info)
    return snapshot


def _git_describe(workdir: Path) -> Dict[str, str]:
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=workdir, stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        return {}
    branch = ""
    try:
        branch = (
            subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=workdir,
                stderr=subprocess.DEVNULL,
            )
            .decode()
            .strip()
        )
    except Exception:
        pass
    status = "clean"
    try:
        porcelain = subprocess.check_output(
            ["git", "status", "--short"], cwd=workdir, stderr=subprocess.DEVNULL
        ).decode().strip()
        if porcelain:
            status = "dirty"
    except Exception:
        pass
    info: Dict[str, str] = {"git_commit": commit, "git_status": status}
    if branch:
        info["git_branch"] = branch
    return info
