PYTHON = python3
ARGS =

.DEFAULT_GOAL := help

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

test:  ## Run tests.
	$(PYTHON) -m pytest $(ARGS)

test-parallel:  ## Run all tests in parallel.
	$(MAKE) test ARGS="-n auto" $(ARGS)

test-linux:  ## Run only the Linux kernel corpus integration tests.
	$(PYTHON) -m pytest -n auto -k "linux/" tests/test_integration.py $(ARGS)

test-sphinx:  ##
	$(PYTHON) -m pytest -n auto -k "sphinx/" tests/test_integration.py $(ARGS)

test-peps:  ## Run only the Python PEPs corpus integration tests.
	$(PYTHON) -m pytest -n auto -k "peps/" tests/test_integration.py $(ARGS)

test-ansible:  ## Run only the Ansible corpus integration tests.
	$(PYTHON) -m pytest -n auto -k "ansible/" tests/test_integration.py $(ARGS)

test-numpy:  ## Run only the NumPy corpus integration tests.
	$(PYTHON) -m pytest -n auto -k "numpy/" tests/test_integration.py $(ARGS)

test-salt:  ## Run only the Salt corpus integration tests.
	$(PYTHON) -m pytest -n auto -k "salt/" tests/test_integration.py $(ARGS)

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

VERSION = $(shell grep '^version' pyproject.toml | head -1 | sed 's/.*"\(.*\)"/\1/')

pre-release:  ## Check if we're ready to publish a new release.
	@echo "Version: $(VERSION)"
	@git tag -l "v$(VERSION)" | grep -q . && echo "FAIL: tag v$(VERSION) already exists" && exit 1 || true
	@$(MAKE) clean
	@$(MAKE) lint-all
	@$(PYTHON) -m build
	@$(PYTHON) -m twine check dist/*
	@echo ""
	@echo "All checks passed. Run 'make release' to publish $(VERSION)."

release:  ## Tag and push a release from version in pyproject.toml.
	@git diff --quiet || (echo "error: uncommitted changes" && exit 1)
	git tag "v$(VERSION)"
	git push origin master --tags

help:  ## Display callable targets.
	@awk -F':.*?## ' '/^[a-zA-Z0-9_.-]+:.*?## / {printf "\033[36m%-24s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST) | sort
