"""Sphinx configuration for MOOD server API documentation."""

from __future__ import annotations

import os
import sys

project = "MOOD server"
copyright = "2026"
author = "MOOD"
release = "0.1"

_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, _root)

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
]

autodoc_member_order = "bysource"
napoleon_google_docstring = True

templates_path = ["_templates"]
exclude_patterns: list[str] = []

html_theme = "alabaster"
html_static_path = ["_static"]
