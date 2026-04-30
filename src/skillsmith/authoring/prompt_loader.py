"""Version-pinned prompt loader for the authoring pipeline.

Reads a fixture markdown file, extracts the HTML-comment version pin,
and returns (text, version). Emits a prompt_loaded event for telemetry
(Phase D wires the actual table; here we just log it).
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

_VERSION_RE = re.compile(r"<!--\s*prompt_version:\s*([^\s]+)\s*-->")


def load_prompt(path: Path | str) -> tuple[str, str]:
    """Load a versioned prompt markdown file.

    Returns (text, version) where version is the parsed version pin or
    "" if no pin is found.
    """
    text = Path(path).read_text(encoding="utf-8")
    m = _VERSION_RE.search(text)
    version = m.group(1) if m else ""
    logger.debug("prompt_loaded path=%s version=%s", path, version or "(none)")
    return text, version
