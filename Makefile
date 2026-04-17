PYTHON = python3
ARGS =

.DEFAULT_GOAL := help

# =====================================================================
# Install
# =====================================================================

clean:  ## Remove all build/temp files.
	@rm -rfv `find . \
		-type d -name __pycache__ \
		-o -type f -name \*.pyc \
		-o -type f -name \*.pyo \
		-o -type f -name \*.bak \
		-o -type f -name \*.orig \
		-o -type f -name \*.rej`
	@rm -rfv \
		*.egg-info \
		.coverage \
		.pytest_cache \
		.ruff_cache/ \
		build/ \
		dist/ \
		htmlcov/

install:  ## Install in editable + user mode
	$(PYTHON) -m pip install -e . --user

# =====================================================================
# Tests
# =====================================================================

test:  ## Run tests.
	$(PYTHON) -m pytest $(ARGS)

test-parallel:  ## Run all tests in parallel.
	$(PYTHON) -m pytest -p xdist -n auto --dist loadgroup $(ARGS)

test-regressions:  ## Run only the local regression fixture tests.
	$(PYTHON) -m pytest -k "local/regressions/" tests/test_integration.py $(ARGS)

test-examples:  ## Run only the local example fixture tests.
	$(PYTHON) -m pytest -k "local/examples/" tests/test_integration.py $(ARGS)

test-docutils:
	$(PYTHON) -m pytest -k "TestDocutils" $(ARGS)

test-last-failed:  ## Re-run tests which failed on last run
	$(PYTHON) -m pytest --last-failed $(ARGS)

# --- corpus integration tests

test-cpython:
	$(PYTHON) -m pytest -n auto -k "cpython/" tests/test_integration.py $(ARGS)

test-peps:
	$(PYTHON) -m pytest -n auto -k "peps/" tests/test_integration.py $(ARGS)

test-sphinx:
	$(PYTHON) -m pytest -n auto -k "sphinx/" tests/test_integration.py $(ARGS)

test-linux:
	$(PYTHON) -m pytest -n auto -k "linux/" tests/test_integration.py $(ARGS)

test-sqlalchemy:
	$(PYTHON) -m pytest -n auto -k "sqlalchemy/" tests/test_integration.py $(ARGS)

test-pytest:
	$(PYTHON) -m pytest -n auto -k "pytest/" tests/test_integration.py $(ARGS)

test-ansible:
	$(PYTHON) -m pytest -n auto -k "ansible/" tests/test_integration.py $(ARGS)

test-numpy:
	$(PYTHON) -m pytest -n auto -k "numpy/" tests/test_integration.py $(ARGS)

test-salt:
	$(PYTHON) -m pytest -n auto -k "salt/" tests/test_integration.py $(ARGS)

# =====================================================================
# Linters
# =====================================================================

_ls = $(if $(FILES), printf '%s\n' $(FILES), git ls-files $(1))

ruff:  ## Run ruff linter.
	@$(call _ls,'*.py') | xargs $(PYTHON) -m ruff check --output-format=concise

black:  ## Run black formatter (check only).
	@$(call _ls,'*.py') | xargs $(PYTHON) -m black --check --safe

lint-toml:  ## Run linter for pyproject.toml.
	@$(call _ls,'*.toml') | xargs toml-sort --check

lint-all:  ## Run all linters.
	$(MAKE) black
	$(MAKE) ruff
	$(MAKE) lint-toml

# =====================================================================
# Fixers
# =====================================================================

fix-ruff:  ## Auto-fix ruff warnings.
	@$(call _ls,'*.py') | xargs $(PYTHON) -m ruff check --fix --output-format=concise $(ARGS)

fix-black:  ## Auto-format with black.
	@$(call _ls,'*.py') | xargs $(PYTHON) -m black

fix-toml:  ## Fix pyproject.toml
	@git ls-files '*.toml' | xargs toml-sort

fix-all:  ## Run all fixers.
	$(MAKE) fix-ruff
	$(MAKE) fix-black
	$(MAKE) fix-toml

# =====================================================================
# Release
# =====================================================================

VERSION = $(shell grep '^version' pyproject.toml | head -1 | sed 's/.*"\(.*\)"/\1/')

lint-release:  ## Run sanity checks against the release / tarball.
	$(PYTHON) -m validate_pyproject -v pyproject.toml
	$(MAKE) clean
	$(PYTHON) -m build
	$(PYTHON) -m twine check --strict dist/*
	rm -rf /tmp/rstwrap-release-venv
	$(PYTHON) -m venv /tmp/rstwrap-release-venv
	/tmp/rstwrap-release-venv/bin/pip install --quiet dist/rstwrap-$(VERSION)-py3-none-any.whl
	installed=$$(/tmp/rstwrap-release-venv/bin/rstwrap --version | awk '{print $$2}'); \
		test "$$installed" = "$(VERSION)" \
		|| (echo "FAIL: installed CLI version $$installed != $(VERSION)" && exit 1)
	rm -rf /tmp/rstwrap-release-venv
	@echo "Release $(VERSION) passed all checks."

pre-release:  ## Check if we're ready to publish a new release.
	@echo "Version: $(VERSION)"
	$(MAKE) clean
	test "$$(git rev-parse --abbrev-ref HEAD)" = "master" \
		|| (echo "FAIL: not on master branch" && exit 1)
	git fetch origin --quiet
	git merge-base --is-ancestor origin/master HEAD \
		|| (echo "FAIL: origin/master has commits not in local master" && exit 1)
	git tag -l "v$(VERSION)" | grep -q . && echo "FAIL: tag v$(VERSION) already exists" && exit 1 || true
	$(MAKE) lint-all
	$(MAKE) lint-release
	@echo ""
	@echo "All checks passed. Run 'make release' to publish $(VERSION)."

release:  ## Tag and push a release from version in pyproject.toml.
	git diff-index --quiet HEAD -- || (echo "error: uncommitted changes" && exit 1)
	git tag "v$(VERSION)"
	git push origin master --tags

# --- misc

help:  ## Display callable targets.
	@awk -F':.*?## ' '/^[a-zA-Z0-9_.-]+:.*?## / {printf "\033[36m%-24s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST) | sort
