"""GitHub-based backup for shadow log JSONL files.

Why this exists:
    Railway containers have ephemeral disk. Every redeploy, restart, or env-var
    change wipes /data/logs. A Railway Volume fixes it, but if the user can't
    or won't attach one, this module provides an alternative: push the JSONL
    files to a separate branch (`data-snapshots`) of the GitHub repo on a
    schedule. Branch is force-updated per file via the REST API — no git
    binary needed in the container.

What gets backed up:
    /data/logs/a2_shadow.jsonl
    /data/logs/a2_outcomes.jsonl
    /data/logs/a2_status.json

What does NOT get backed up:
    Anything else. No code, no .env, no secrets.

Required env vars:
    GITHUB_TOKEN     Fine-grained PAT with `Contents: Read & Write` scope,
                     restricted to the single repo. Set in Railway service vars.
    GITHUB_REPO      "owner/repo", e.g. "GoldenRodger5/singal-flow"

Optional env vars:
    GITHUB_BACKUP_BRANCH    Default "data-snapshots"
    GITHUB_BACKUP_BASE      Branch to seed from if backup branch doesn't exist.
                            Default "main".

Failure semantics:
    Never raises. Every error is logged and the function returns False so the
    caller (the orchestrator loop) can keep running. A bot that can't back up
    is still a bot doing its job.
"""
from __future__ import annotations

import base64
import os
from datetime import datetime, timezone
from pathlib import Path

import httpx

from helios.ops.logging import get_logger

log = get_logger(__name__)

API_BASE = "https://api.github.com"

BACKUP_FILES = (
    "a2_shadow.jsonl",
    "a2_outcomes.jsonl",
    "a2_status.json",
)


def _env(name: str, default: str | None = None) -> str | None:
    v = os.getenv(name)
    return v if v is not None else default


async def _gh_get(client: httpx.AsyncClient, url: str, token: str) -> httpx.Response:
    return await client.get(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )


async def _gh_put(client: httpx.AsyncClient, url: str, token: str, body: dict) -> httpx.Response:
    return await client.put(
        url,
        json=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )


async def _gh_post(client: httpx.AsyncClient, url: str, token: str, body: dict) -> httpx.Response:
    return await client.post(
        url,
        json=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )


async def _ensure_branch(
    client: httpx.AsyncClient, owner: str, repo: str, branch: str, base_branch: str, token: str
) -> bool:
    """Create `branch` from `base_branch` if it doesn't already exist."""
    # Does our backup branch already exist?
    resp = await _gh_get(client, f"{API_BASE}/repos/{owner}/{repo}/git/refs/heads/{branch}", token)
    if resp.status_code == 200:
        return True

    # Get the base branch's HEAD sha
    resp = await _gh_get(client, f"{API_BASE}/repos/{owner}/{repo}/git/refs/heads/{base_branch}", token)
    if resp.status_code != 200:
        log.warning("backup_base_branch_missing", base=base_branch, status=resp.status_code)
        return False
    base_sha = resp.json().get("object", {}).get("sha")
    if not base_sha:
        return False

    # Create our branch from base
    resp = await _gh_post(
        client,
        f"{API_BASE}/repos/{owner}/{repo}/git/refs",
        token,
        {"ref": f"refs/heads/{branch}", "sha": base_sha},
    )
    if resp.status_code in (200, 201):
        log.info("backup_branch_created", branch=branch, from_=base_branch)
        return True
    log.warning("backup_branch_create_failed", status=resp.status_code, body=resp.text[:200])
    return False


async def _upsert_file(
    client: httpx.AsyncClient,
    owner: str,
    repo: str,
    branch: str,
    remote_path: str,
    content_bytes: bytes,
    commit_message: str,
    token: str,
) -> bool:
    """Create-or-update a file in the backup branch via the Contents API."""
    # Fetch current sha (if any) so we can update vs create
    existing_sha: str | None = None
    resp = await _gh_get(
        client,
        f"{API_BASE}/repos/{owner}/{repo}/contents/{remote_path}?ref={branch}",
        token,
    )
    if resp.status_code == 200:
        existing_sha = resp.json().get("sha")

    body: dict = {
        "message": commit_message,
        "content": base64.b64encode(content_bytes).decode("ascii"),
        "branch": branch,
    }
    if existing_sha:
        body["sha"] = existing_sha

    resp = await _gh_put(
        client,
        f"{API_BASE}/repos/{owner}/{repo}/contents/{remote_path}",
        token,
        body,
    )
    if resp.status_code in (200, 201):
        return True
    log.warning(
        "backup_upsert_failed",
        path=remote_path, status=resp.status_code, body=resp.text[:200],
    )
    return False


async def backup_to_github(
    logs_dir: str | Path = "/data/logs",
    files: tuple[str, ...] = BACKUP_FILES,
) -> bool:
    """Push the named files from `logs_dir` to the GitHub backup branch.

    Returns True if *all* present files were pushed successfully; False if any
    step failed (still safe — never raises).
    """
    token = _env("GITHUB_TOKEN")
    repo = _env("GITHUB_REPO")  # "owner/repo"
    branch = _env("GITHUB_BACKUP_BRANCH", "data-snapshots") or "data-snapshots"
    base_branch = _env("GITHUB_BACKUP_BASE", "main") or "main"

    if not token or not repo or "/" not in repo:
        log.debug("backup_disabled_missing_env", has_token=bool(token), repo=repo)
        return False
    owner, repo_name = repo.split("/", 1)

    logs_path = Path(logs_dir)
    candidates: list[Path] = []
    for fname in files:
        p = logs_path / fname
        if p.exists() and p.is_file():
            candidates.append(p)
    if not candidates:
        log.debug("backup_nothing_to_push", logs_dir=str(logs_path))
        return True  # nothing to do is success

    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if not await _ensure_branch(client, owner, repo_name, branch, base_branch, token):
                return False

            ok = True
            for src in candidates:
                content = src.read_bytes()
                size_kb = len(content) / 1024.0
                msg = f"backup({src.name}) @ {timestamp} [{size_kb:.1f} KB]"
                # Remote path: just the file basename at root of backup branch
                ok = await _upsert_file(
                    client, owner, repo_name, branch, src.name, content, msg, token
                ) and ok
            log.info(
                "backup_complete",
                files=[c.name for c in candidates], timestamp=timestamp, success=ok,
            )
            return ok
    except Exception as e:  # noqa: BLE001
        log.warning("backup_unexpected_failure", error=str(e))
        return False
