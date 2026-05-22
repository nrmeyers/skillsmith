"""Contract artifact: parsing, validation, and file management.

A contract is a markdown file with YAML frontmatter written by the paid LLM
to state task intent and domain tags. It drives domain retrieval (Phase 2)
and gate evaluation (Phase 3).

Format::

    ---
    phase: build
    task_slug: add-auth-middleware
    domain_tags:
      - NestJS
      - JWT validation
    scope:
      touches:
        - "src/auth/**"
      avoids:
        - "src/billing/**"
    success_criteria:
      - "Existing auth tests still pass"
    related_contracts: []
    created_at: 2026-05-21T14:32:11Z
    ---

    # Add Auth Middleware

    <task description prose>
"""

from __future__ import annotations

import fnmatch
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ContractScope:
    touches: list[str]  # globs; may be empty
    avoids: list[str]  # globs; may be empty


@dataclass(frozen=True)
class Contract:
    path: Path
    phase: str
    task_slug: str
    domain_tags: list[str]
    scope: ContractScope
    success_criteria: list[str]
    related_contracts: list[Path]
    created_at: datetime | None
    body: str


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class ContractError(Exception):
    """Base for contract problems."""


class ContractMalformed(ContractError):
    """Frontmatter missing, schema invalid, etc."""


class ContractPhaseMismatch(ContractError):
    """Contract's phase field doesn't match .skillsmith/phase."""


# ---------------------------------------------------------------------------
# Frontmatter parser (inline — no python-frontmatter dependency required)
# ---------------------------------------------------------------------------


def _split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Split markdown+frontmatter into (metadata_dict, body_str).

    Raises ContractMalformed if the frontmatter delimiter is missing or the
    YAML cannot be parsed.
    """
    if not text.startswith("---"):
        raise ContractMalformed("Contract must begin with '---' YAML frontmatter delimiter")

    # Find closing delimiter
    rest = text[3:].lstrip("\n")
    end_match = re.search(r"^---\s*$", rest, re.MULTILINE)
    if not end_match:
        raise ContractMalformed("Contract frontmatter is not closed with a '---' delimiter")

    fm_text = rest[: end_match.start()]
    body = rest[end_match.end() :].lstrip("\n")

    try:
        data = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError as exc:
        raise ContractMalformed(f"Contract frontmatter YAML is invalid: {exc}") from exc

    if not isinstance(data, dict):
        raise ContractMalformed("Contract frontmatter must be a YAML mapping")

    return data, body  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def parse_contract(path: Path) -> Contract:
    """Read and validate a contract file. Raises ContractMalformed on errors."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ContractMalformed(f"Cannot read contract file {path}: {exc}") from exc

    data, body = _split_frontmatter(text)

    # Required fields
    phase = data.get("phase")
    if not phase or not isinstance(phase, str):
        raise ContractMalformed("Contract 'phase' field is required and must be a non-empty string")

    task_slug = data.get("task_slug")
    if not task_slug or not isinstance(task_slug, str):
        raise ContractMalformed("Contract 'task_slug' field is required and must be a non-empty string")

    domain_tags_raw = data.get("domain_tags")
    if not domain_tags_raw or not isinstance(domain_tags_raw, list):
        raise ContractMalformed(
            "Contract 'domain_tags' field is required and must be a non-empty list"
        )
    domain_tags = [str(t) for t in domain_tags_raw]
    if not domain_tags:
        raise ContractMalformed("Contract 'domain_tags' must be non-empty")

    # Optional scope
    scope_raw = data.get("scope") or {}
    scope = ContractScope(
        touches=[str(g) for g in (scope_raw.get("touches") or [])],
        avoids=[str(g) for g in (scope_raw.get("avoids") or [])],
    )

    success_criteria = [str(c) for c in (data.get("success_criteria") or [])]

    related_raw = data.get("related_contracts") or []
    related_contracts: list[Path] = []
    for r in related_raw:
        rp = Path(str(r))
        if not rp.is_absolute():
            rp = path.parent / rp
        related_contracts.append(rp)

    # created_at — optional; fall back to file mtime
    created_at: datetime | None = None
    raw_ts = data.get("created_at")
    if raw_ts:
        try:
            if isinstance(raw_ts, str):
                created_at = datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
            elif isinstance(raw_ts, datetime):
                created_at = raw_ts
        except (ValueError, TypeError):
            created_at = None
    if created_at is None:
        try:
            mtime = path.stat().st_mtime
            created_at = datetime.fromtimestamp(mtime, tz=timezone.utc)
        except OSError:
            pass

    return Contract(
        path=path.resolve(),
        phase=phase,
        task_slug=task_slug,
        domain_tags=domain_tags,
        scope=scope,
        success_criteria=success_criteria,
        related_contracts=related_contracts,
        created_at=created_at,
        body=body,
    )


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_contract(contract: Contract, project_root: Path) -> list[str]:
    """Return a list of issues (empty = valid). Does not raise."""
    issues: list[str] = []

    # Phase match check
    phase_file = project_root / ".skillsmith" / "phase"
    if phase_file.exists():
        try:
            phase_data = yaml.safe_load(phase_file.read_text(encoding="utf-8")) or {}
            if isinstance(phase_data, dict):
                active_phase = str(phase_data.get("phase", "")).strip()
            else:
                active_phase = ""
            if active_phase and active_phase != contract.phase:
                issues.append(
                    f"Contract phase '{contract.phase}' does not match active phase "
                    f"'{active_phase}' in .skillsmith/phase"
                )
        except Exception:
            pass

    # Related contracts existence
    for rp in contract.related_contracts:
        if not rp.exists():
            issues.append(f"Related contract not found: {rp}")

    # domain_tags non-empty (already enforced by parse, but belt+suspenders)
    if not contract.domain_tags:
        issues.append("domain_tags must be non-empty")

    # scope.touches globs valid syntax
    for pattern in contract.scope.touches + contract.scope.avoids:
        try:
            fnmatch.translate(pattern)
        except Exception:
            issues.append(f"Invalid glob pattern in scope: {pattern!r}")

    return issues


# ---------------------------------------------------------------------------
# File discovery
# ---------------------------------------------------------------------------


def list_contracts_for_phase(project_root: Path, phase: str) -> list[Path]:
    """Return all .skillsmith/contracts/<phase>/*.md sorted newest-first by mtime."""
    contracts_dir = project_root / ".skillsmith" / "contracts" / phase
    if not contracts_dir.is_dir():
        return []
    files = [f for f in contracts_dir.glob("*.md") if f.is_file()]
    return sorted(files, key=lambda f: f.stat().st_mtime, reverse=True)


@dataclass(frozen=True)
class CodeIndexerQuery:
    """Parameters for a code-indexer search derived from a contract."""

    repo: str
    semantic_q: str
    lexical_q: str | None
    path_globs: list[str]


def code_indexer_query_params(contract: "Contract", project_root: Path) -> CodeIndexerQuery:
    """Build code-indexer query parameters from a contract.

    Derives the repo slug from `git remote get-url origin` (GitHub owner__repo form).
    Falls back to the project directory name when git remote is unavailable.
    """
    import re
    import subprocess

    # Derive repo slug
    repo = project_root.name
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=5, cwd=project_root,
        )
        url = result.stdout.strip()
        # github.com/owner/repo or git@github.com:owner/repo → owner__repo
        m = re.search(r"[:/]([^/]+)/([^/]+?)(?:\.git)?$", url)
        if m:
            repo = f"{m.group(1)}__{m.group(2)}"
    except Exception:
        pass

    body = (contract.body or "").strip()
    first_line = body.split("\n")[0].lstrip("# ").strip() if body else ""
    semantic_q = first_line or contract.task_slug

    lexical_q = " ".join(contract.domain_tags) if contract.domain_tags else None
    path_globs = list(contract.scope.touches) if contract.scope and contract.scope.touches else []

    return CodeIndexerQuery(
        repo=repo,
        semantic_q=semantic_q,
        lexical_q=lexical_q,
        path_globs=path_globs,
    )


def latest_contract(project_root: Path, phase: str | None = None) -> Path | None:
    """Most recently modified contract (optionally filtered by phase)."""
    if phase:
        files = list_contracts_for_phase(project_root, phase)
        return files[0] if files else None

    # No phase filter — scan all phases
    contracts_root = project_root / ".skillsmith" / "contracts"
    if not contracts_root.is_dir():
        return None

    all_files: list[Path] = []
    for phase_dir in contracts_root.iterdir():
        if phase_dir.is_dir():
            all_files.extend(f for f in phase_dir.glob("*.md") if f.is_file())

    if not all_files:
        return None

    return max(all_files, key=lambda f: f.stat().st_mtime)
