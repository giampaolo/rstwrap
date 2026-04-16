import pathlib
import subprocess

CLONE_DIR = pathlib.Path("/tmp/rstwrap-cpython")
SPHINX_CLONE_DIR = pathlib.Path("/tmp/rstwrap-sphinx")
SQLALCHEMY_CLONE_DIR = pathlib.Path("/tmp/rstwrap-sqlalchemy")
PYTEST_CLONE_DIR = pathlib.Path("/tmp/rstwrap-pytest")
LINUX_CLONE_DIR = pathlib.Path("/tmp/rstwrap-linux")
PEPS_CLONE_DIR = pathlib.Path("/tmp/rstwrap-peps")
ANSIBLE_CLONE_DIR = pathlib.Path("/tmp/rstwrap-ansible")
NUMPY_CLONE_DIR = pathlib.Path("/tmp/rstwrap-numpy")
SALT_CLONE_DIR = pathlib.Path("/tmp/rstwrap-salt")

_REPOS = [
    {
        "url": "https://github.com/python/cpython",
        "clone_dir": CLONE_DIR,
        "branch": "main",
        "sparse_dir": "Doc/",
    },
    {
        "url": "https://github.com/sphinx-doc/sphinx",
        "clone_dir": SPHINX_CLONE_DIR,
        "branch": "master",
        "sparse_dir": "doc/",
    },
    {
        "url": "https://github.com/sqlalchemy/sqlalchemy",
        "clone_dir": SQLALCHEMY_CLONE_DIR,
        "branch": "main",
        "sparse_dir": "doc/build/",
    },
    {
        "url": "https://github.com/pytest-dev/pytest",
        "clone_dir": PYTEST_CLONE_DIR,
        "branch": "main",
        "sparse_dir": "doc/en/",
    },
    {
        "url": "https://github.com/torvalds/linux",
        "clone_dir": LINUX_CLONE_DIR,
        "branch": "master",
        "sparse_dir": "Documentation/",
    },
    {
        "url": "https://github.com/python/peps",
        "clone_dir": PEPS_CLONE_DIR,
        "branch": "main",
        "sparse_dir": "peps/",
    },
    {
        "url": "https://github.com/ansible/ansible-documentation",
        "clone_dir": ANSIBLE_CLONE_DIR,
        "branch": "devel",
        "sparse_dir": "docs/docsite/rst/",
    },
    {
        "url": "https://github.com/numpy/numpy",
        "clone_dir": NUMPY_CLONE_DIR,
        "branch": "main",
        "sparse_dir": "doc/source/",
    },
    {
        "url": "https://github.com/saltstack/salt",
        "clone_dir": SALT_CLONE_DIR,
        "branch": "master",
        "sparse_dir": "doc/",
    },
]


def _clone_repo(url, clone_dir, branch, sparse_dir):
    """Clone *url* into *clone_dir* (sparse, *sparse_dir* only).

    Skipped if the directory already exists.
    """
    if clone_dir.exists():
        return
    subprocess.run(
        [
            "git",
            "clone",
            "--filter=blob:none",
            "--sparse",
            "--branch",
            branch,
            "--single-branch",
            "--depth",
            "1",
            url,
            str(clone_dir),
        ],
        check=True,
    )
    subprocess.run(
        ["git", "sparse-checkout", "set", sparse_dir],
        cwd=clone_dir,
        check=True,
    )


def pytest_sessionstart(session):
    """Clone all external repos before collection so that parametrize
    lists are available when pytest-xdist spawns workers.
    """
    for repo in _REPOS:
        _clone_repo(**repo)


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
