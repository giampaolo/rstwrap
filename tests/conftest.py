import pathlib
import subprocess

REPO_URL = "https://github.com/python/cpython"
CLONE_DIR = pathlib.Path("/tmp/rst-wrap-lines-cpython")


def clone_cpython_repo():
    if CLONE_DIR.exists():
        return
    subprocess.run(
        [
            "git",
            "clone",
            "--filter=blob:none",
            "--sparse",
            "--branch",
            "main",
            "--single-branch",
            "--depth",
            "1",
            REPO_URL,
            str(CLONE_DIR),
        ],
        check=True,
    )
    subprocess.run(
        ["git", "sparse-checkout", "set", "Doc/"],
        cwd=CLONE_DIR,
        check=True,
    )


def pytest_sessionstart(session):
    clone_cpython_repo()


def pytest_collection_modifyitems(config, items):
    # Deselect slow tests unless the user explicitly targets them via -m.
    if config.option.markexpr:
        return
    slow = [item for item in items if item.get_closest_marker("slow")]
    if slow:
        config.hook.pytest_deselected(items=slow)
        items[:] = [
            item for item in items if not item.get_closest_marker("slow")
        ]
