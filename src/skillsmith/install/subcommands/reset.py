"""``skillsmith reset`` — nuclear reset for profile overrides.

Commands:
    skillsmith reset                   — reset active profile overrides (prompts)
    skillsmith reset --profile <name>  — reset a specific profile
    skillsmith reset --all-profiles    — reset every profile
    skillsmith reset --include-domain  — also wipe and re-ingest domain.duck
    skillsmith reset --yes             — skip confirmation
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path
from typing import Any


def _reingest_profile_defaults(profile_name: str) -> list[str]:
    """Re-ingest shipped default system+workflow skills into a profile's datastore."""
    import skillsmith
    from skillsmith.profiles import profile_datastore_path

    packs_root = Path(skillsmith.__file__).resolve().parent / "_packs"
    ingested: list[str] = []

    if not packs_root.is_dir():
        return ingested

    try:
        import yaml

        for yaml_file in sorted(packs_root.rglob("*.yaml")):
            if yaml_file.name == "pack.yaml":
                continue
            try:
                data = yaml.safe_load(yaml_file.read_text(encoding="utf-8")) or {}
            except Exception:
                continue
            skill_class = data.get("skill_class", "")
            if skill_class not in ("system", "workflow"):
                continue

            # Ingest into the profile datastore
            ds_path = profile_datastore_path(profile_name)
            try:
                from skillsmith.storage.vector_store import open_or_create

                with open_or_create(str(ds_path)) as store:
                    # Minimal upsert — insert or replace skill row.
                    skill_id = data.get("skill_id") or yaml_file.stem
                    raw_prose = data.get("raw_prose", "")
                    store.execute(
                        """
                        INSERT OR REPLACE INTO skills
                        (skill_id, skill_class, raw_prose)
                        VALUES (?, ?, ?)
                        """,
                        [skill_id, skill_class, raw_prose],
                    )
                ingested.append(skill_id)
            except Exception:
                continue
    except ImportError:
        pass

    return ingested


def _reset_profile(
    name: str,
    include_domain: bool = False,
) -> dict[str, Any]:
    """Reset a single profile: delete overrides, re-ingest defaults."""
    from skillsmith.profiles import get_profile, profile_skills_dir

    try:
        profile = get_profile(name)
    except KeyError:
        return {"profile": name, "error": f"Profile '{name}' not found"}

    # Delete override files
    skills = profile_skills_dir(name)
    deleted_overrides: list[str] = []
    for class_dir in ("system", "workflow"):
        d = skills / class_dir
        if d.exists():
            for f in sorted(d.iterdir()):
                if f.is_file():
                    deleted_overrides.append(str(f.relative_to(skills)))
                    f.unlink()

    # Re-ingest defaults
    ingested = _reingest_profile_defaults(name)

    result: dict[str, Any] = {
        "profile": name,
        "deleted_overrides": deleted_overrides,
        "reingested_defaults": ingested,
    }

    if include_domain:
        from skillsmith.profiles import domain_datastore_path

        domain_path = domain_datastore_path()
        if domain_path.exists():
            domain_path.unlink()
        # Full re-embed is triggered by seed_corpus
        try:
            from skillsmith.install.subcommands import seed_corpus

            seed_result = seed_corpus.seed(duck_path=domain_path)
            result["domain_reset"] = seed_result
        except Exception as exc:
            result["domain_reset"] = {"error": str(exc)}

    return result


def reset(
    profile: str | None = None,
    all_profiles: bool = False,
    include_domain: bool = False,
    yes: bool = False,
) -> dict[str, Any]:
    """Run the reset flow. Returns a summary dict."""
    from skillsmith.profiles import detect_profile, load_profiles_config

    t0 = time.monotonic()

    # Determine which profiles to reset
    if all_profiles:
        config = load_profiles_config()
        target_names = list(config.profiles.keys())
        target_names.insert(0, "default")
        # De-duplicate while preserving order
        seen: set[str] = set()
        targets: list[str] = []
        for n in target_names:
            if n not in seen:
                targets.append(n)
                seen.add(n)
        confirmation_target = "ALL profiles"
    else:
        if profile:
            targets = [profile]
        else:
            active = detect_profile(cwd=Path.cwd())
            targets = [active.name]
        confirmation_target = f"profile '{targets[0]}'"

    # Confirmation
    if not yes:
        if sys.stdin.isatty():
            prompt = f"  Reset {confirmation_target}? All override files will be deleted. Type 'yes' to confirm: "
            confirm = input(prompt).strip()
            if confirm.lower() != "yes":
                return {"cancelled": True}
        else:
            # Non-TTY without --yes: refuse
            print(
                f"  [error] Resetting {confirmation_target} requires --yes in non-interactive mode.",
                file=sys.stderr,
            )
            return {"error": "confirmation required"}

    results = [_reset_profile(name, include_domain=include_domain) for name in targets]

    summary: dict[str, Any] = {
        "reset_profiles": results,
        "duration_ms": int((time.monotonic() - t0) * 1000),
    }
    return summary


def add_parser(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],  # pyright: ignore[reportPrivateUsage]
) -> None:
    p = subparsers.add_parser(
        "reset",
        help="Reset profile overrides and re-ingest defaults.",
    )
    p.add_argument(
        "--profile",
        default=None,
        help="Target a specific profile (default: active profile for cwd).",
    )
    p.add_argument(
        "--all-profiles",
        dest="all_profiles",
        action="store_true",
        help="Reset every configured profile.",
    )
    p.add_argument(
        "--include-domain",
        dest="include_domain",
        action="store_true",
        help="Also wipe and re-ingest the shared domain datastore (slow).",
    )
    p.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation prompt (dangerous).",
    )
    p.set_defaults(func=_run)


def _run(args: argparse.Namespace) -> int:
    result = reset(
        profile=args.profile,
        all_profiles=args.all_profiles,
        include_domain=args.include_domain,
        yes=args.yes,
    )
    if result.get("cancelled"):
        print("  Reset cancelled.")
        return 0
    if result.get("error"):
        print(f"  [error] {result['error']}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


# Suppress unused import
_ = shutil
