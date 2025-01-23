#!/usr/bin/env python
"""Extract changelog entries for a specific version and format them for GitHub Actions."""

import re
import sys
from pathlib import Path

version = sys.argv[1]

# Read changelog
content = Path("CHANGELOG.rst").read_text()

# Find the section for this version
pattern = (
    rf"(?:\*+\n{re.escape(version)}\s.*?\n\*+\n\n)(?P<body>.*?)(?:\n\n(?=\*+|----))"
)
match = re.search(pattern, content, re.DOTALL)

if match:
    # Get the matched section
    section = match.group("body").strip()
    # Format for GitHub Actions output
    section = section.replace("%", "%25").replace("\n", "%0A").replace("\r", "%0D")
else:
    section = "(No changelog entry for this version)"
print(f"::set-output name=changelog::{section}")
