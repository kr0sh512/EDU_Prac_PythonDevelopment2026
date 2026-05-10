"""DoIt build automation for the MOOD project.

Targets
-------
pot        -- extract translatable strings from source into a .pot template
update_po  -- update the existing .po file from the .pot template
compile_mo -- compile the .po translation into a binary .mo file
i18n       -- full translation pipeline (pot -> update_po -> compile_mo)
html       -- generate HTML documentation with Sphinx  [DEFAULT]
test       -- run client+server integration tests (requires compiled i18n)
"""

import pathlib
import shutil
import sys

from doit.task import clean_targets

# Resolve tool executables that live next to the current Python interpreter
# so the commands work regardless of how PATH is configured.
_BIN = pathlib.Path(sys.executable).parent
PYBABEL = str(_BIN / "pybabel")
SPHINX_BUILD = str(_BIN / "sphinx-build")
PYTEST = str(_BIN / "pytest")

# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------

LOCALE_DIR = pathlib.Path("mood/server/locale")
PO_FILE = LOCALE_DIR / "ru_RU.UTF8" / "LC_MESSAGES" / "mood_server.po"
MO_FILE = LOCALE_DIR / "ru_RU.UTF8" / "LC_MESSAGES" / "mood_server.mo"
POT_FILE = LOCALE_DIR / "mood_server.pot"
DOC_BUILD = pathlib.Path("mood/doc")
DOMAIN = "mood_server"
BABEL_CFG = "babel.cfg"

# ---------------------------------------------------------------------------
# DoIt global config — html is the default target
# ---------------------------------------------------------------------------

DOIT_CONFIG = {"default_tasks": ["html"]}

# ---------------------------------------------------------------------------
# Translation step targets
# ---------------------------------------------------------------------------


def task_pot():
    """Step 1 — extract translatable strings into a .pot template."""
    server_sources = [
        str(p) for p in sorted(pathlib.Path("mood/server").glob("**/*.py"))
    ]
    return {
        "actions": [
            f"{PYBABEL} extract -F {BABEL_CFG} -o {POT_FILE} mood/server",
        ],
        "file_dep": server_sources + [BABEL_CFG],
        "targets": [str(POT_FILE)],
        "clean": [clean_targets],
    }


def task_update_po():
    """Step 2 — update the .po translation file from the .pot template."""
    return {
        "actions": [
            f"{PYBABEL} update -i {POT_FILE} -d {LOCALE_DIR} -D {DOMAIN}",
        ],
        "file_dep": [str(POT_FILE)],
        "targets": [str(PO_FILE)],
        "clean": [clean_targets],
    }


def task_compile_mo():
    """Step 3 — compile the .po translation into a binary .mo file."""
    return {
        "actions": [
            f"{PYBABEL} compile -i {PO_FILE} -o {MO_FILE}",
        ],
        "file_dep": [str(PO_FILE)],
        "targets": [str(MO_FILE)],
        "clean": [clean_targets],
    }


# ---------------------------------------------------------------------------
# Composite targets
# ---------------------------------------------------------------------------


def task_i18n():
    """Full i18n generation — depends on: pot, update_po, compile_mo."""
    return {
        "actions": None,
        "task_dep": ["pot", "update_po", "compile_mo"],
        # Remove all generated translation artefacts (pot + mo).
        # The .po file is human-authored source and is NOT removed.
        "clean": [
            lambda: POT_FILE.unlink(missing_ok=True),
            lambda: MO_FILE.unlink(missing_ok=True),
        ],
    }


def task_html():
    """Generate HTML documentation with Sphinx (default target)."""
    doc_sources = [
        str(p) for p in sorted(pathlib.Path("doc/source").rglob("*")) if p.is_file()
    ]
    return {
        "actions": [
            f"{SPHINX_BUILD} -M html doc/source {DOC_BUILD}",
        ],
        "file_dep": doc_sources,
        "targets": [str(DOC_BUILD / "html" / "index.html")],
        "task_dep": ["i18n"],
        # Use shutil.rmtree to remove the entire build directory.
        "clean": [
            (shutil.rmtree, [str(DOC_BUILD)], {"ignore_errors": True}),
        ],
    }


def task_test():
    """Run client+server integration tests (depends on i18n for Russian replies)."""
    return {
        "actions": [
            f"{PYTEST} tests/ -v",
        ],
        "task_dep": ["i18n"],
        "clean": [clean_targets],
    }
