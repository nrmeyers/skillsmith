"""Tests for skillsmith.contracts — parsing, validation, and file discovery."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_contract(
    path: Path,
    *,
    phase: str = "build",
    task_slug: str = "test-task",
    domain_tags: list[str] | None = None,
    scope: dict | None = None,
    success_criteria: list[str] | None = None,
    related_contracts: list[str] | None = None,
    created_at: str | None = None,
    body: str = "Test task description.\n",
    extra_fields: dict | None = None,
) -> Path:
    fm: dict = {
        "phase": phase,
        "task_slug": task_slug,
        "domain_tags": domain_tags or ["NestJS", "JWT"],
        "scope": scope or {"touches": [], "avoids": []},
        "success_criteria": success_criteria or [],
        "related_contracts": related_contracts or [],
    }
    if created_at:
        fm["created_at"] = created_at
    if extra_fields:
        fm.update(extra_fields)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{yaml.dump(fm)}---\n\n{body}", encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# parse_contract — valid cases
# ---------------------------------------------------------------------------


def test_parse_contract_minimal_valid(tmp_path: Path):
    from skillsmith.contracts import parse_contract

    f = _write_contract(tmp_path / "c.md")
    contract = parse_contract(f)
    assert contract.phase == "build"
    assert contract.task_slug == "test-task"
    assert contract.domain_tags == ["NestJS", "JWT"]
    assert contract.body.strip() == "Test task description."


def test_parse_contract_full_fields(tmp_path: Path):
    from skillsmith.contracts import parse_contract

    f = _write_contract(
        tmp_path / "c.md",
        scope={"touches": ["src/auth/**"], "avoids": ["src/billing/**"]},
        success_criteria=["Tests pass"],
        created_at="2026-05-21T14:32:11Z",
        body="Full contract body.\n",
    )
    c = parse_contract(f)
    assert c.scope.touches == ["src/auth/**"]
    assert c.scope.avoids == ["src/billing/**"]
    assert c.success_criteria == ["Tests pass"]
    assert c.created_at is not None
    assert c.created_at.year == 2026
    assert c.body.strip() == "Full contract body."


def test_parse_contract_related_contracts_resolved(tmp_path: Path):
    from skillsmith.contracts import parse_contract

    related = tmp_path / "related.md"
    _write_contract(related)
    f = _write_contract(tmp_path / "c.md", related_contracts=["related.md"])
    c = parse_contract(f)
    assert len(c.related_contracts) == 1
    assert c.related_contracts[0].is_absolute()


# ---------------------------------------------------------------------------
# parse_contract — error cases
# ---------------------------------------------------------------------------


def test_parse_contract_missing_frontmatter(tmp_path: Path):
    from skillsmith.contracts import ContractMalformed, parse_contract

    f = tmp_path / "bad.md"
    f.write_text("No frontmatter here.\n")
    with pytest.raises(ContractMalformed, match="---"):
        parse_contract(f)


def test_parse_contract_empty_domain_tags(tmp_path: Path):
    from skillsmith.contracts import ContractMalformed, parse_contract

    f = tmp_path / "bad.md"
    f.write_text("---\nphase: build\ntask_slug: t\ndomain_tags: []\n---\n\nbody\n")
    with pytest.raises(ContractMalformed, match="domain_tags"):
        parse_contract(f)


def test_parse_contract_missing_required_fields(tmp_path: Path):
    from skillsmith.contracts import ContractMalformed, parse_contract

    f = tmp_path / "bad.md"
    f.write_text("---\ntask_slug: t\ndomain_tags: [tag]\n---\n\nbody\n")
    with pytest.raises(ContractMalformed, match="phase"):
        parse_contract(f)


# ---------------------------------------------------------------------------
# validate_contract
# ---------------------------------------------------------------------------


def test_validate_contract_phase_mismatch(tmp_path: Path):
    from skillsmith.contracts import parse_contract, validate_contract

    # Write a phase file saying 'design'
    phase_file = tmp_path / ".skillsmith" / "phase"
    phase_file.parent.mkdir(parents=True)
    phase_file.write_text("phase: design\n")

    f = _write_contract(tmp_path / "c.md", phase="build")
    c = parse_contract(f)
    issues = validate_contract(c, tmp_path)
    assert any("design" in i and "build" in i for i in issues)


def test_validate_contract_related_contracts_missing(tmp_path: Path):
    from skillsmith.contracts import parse_contract, validate_contract

    f = _write_contract(tmp_path / "c.md", related_contracts=["nonexistent.md"])
    c = parse_contract(f)
    issues = validate_contract(c, tmp_path)
    assert any("nonexistent" in i for i in issues)


def test_validate_contract_valid(tmp_path: Path):
    from skillsmith.contracts import parse_contract, validate_contract

    f = _write_contract(tmp_path / "c.md")
    c = parse_contract(f)
    issues = validate_contract(c, tmp_path)
    assert issues == []


# ---------------------------------------------------------------------------
# list_contracts_for_phase and latest_contract
# ---------------------------------------------------------------------------


def test_list_contracts_for_phase_mtime_order(tmp_path: Path):
    import time

    from skillsmith.contracts import list_contracts_for_phase

    _write_contract(tmp_path / ".skillsmith" / "contracts" / "build" / "old.md")
    time.sleep(0.01)
    _write_contract(tmp_path / ".skillsmith" / "contracts" / "build" / "new.md")

    files = list_contracts_for_phase(tmp_path, "build")
    assert len(files) == 2
    assert files[0].name == "new.md"


def test_list_contracts_for_phase_missing_dir(tmp_path: Path):
    from skillsmith.contracts import list_contracts_for_phase

    files = list_contracts_for_phase(tmp_path, "nonexistent-phase")
    assert files == []


def test_latest_contract_no_phase_filter(tmp_path: Path):
    import time

    from skillsmith.contracts import latest_contract

    _write_contract(tmp_path / ".skillsmith" / "contracts" / "build" / "build.md")
    time.sleep(0.01)
    _write_contract(tmp_path / ".skillsmith" / "contracts" / "spec" / "spec.md")

    latest = latest_contract(tmp_path)
    assert latest is not None
    assert latest.name == "spec.md"
