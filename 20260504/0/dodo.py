from pathlib import Path

import tomllib

PROJECT = "wordcount"
lang = "ru_RU.UTF-8"

with open("pyproject.toml", "rb") as f:
    _meta = tomllib.load(f)
VERSION = _meta["project"]["version"]

WHEEL = f"dist/{PROJECT}-{VERSION}-py3-none-any.whl"
SDIST = f"dist/{PROJECT}-{VERSION}.tar.gz"
PO = f"po/{lang}/LC_MESSAGES/{PROJECT}.po"
MO = f"{PROJECT}/{lang}/LC_MESSAGES/{PROJECT}.mo"


def task_mo():
    """Compile .po -> .mo for all languages"""
    SPATH = Path("po") / lang / "LC_MESSAGES"
    DPATH = Path(PROJECT) / lang / "LC_MESSAGES"
    DPATH.mkdir(parents=True, exist_ok=True)
    return {
        "actions": [
            f"pybabel compile -D {PROJECT} -l {lang} -i {SPATH}/{PROJECT}.po -d {PROJECT}",
        ],
        "file_dep": [PO],
        "targets": [MO],
    }


def task_wheel():
    """Build wheel distribution"""
    return {
        "actions": ["python -m build -n -w"],
        "task_dep": ["mo"],
        "file_dep": ["pyproject.toml", MO],
        "targets": [WHEEL],
    }


def task_dist():
    """Build source distribution"""
    return {
        "actions": ["python -m build -n -s"],
        "task_dep": ["mo"],
        "file_dep": ["pyproject.toml", MO],
        "targets": [SDIST],
    }
