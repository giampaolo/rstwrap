PYTHON = python3
ARGS =

.DEFAULT_GOAL := help

# ===================================================================
# Clean
# ===================================================================

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

# ===================================================================
# Tests
# ===================================================================

test:  ## Run tests.
	$(PYTHON) -m pytest $(ARGS)

# ===================================================================
# Linters
# ===================================================================

_ls = $(if $(FILES), printf '%s\n' $(FILES), git ls-files $(1))

ruff:  ## Run ruff linter.
	@$(call _ls,'*.py') | xargs $(PYTHON) -m ruff check --output-format=concise

black:  ## Run black formatter (check only).
	@$(call _ls,'*.py') | xargs $(PYTHON) -m black --check --safe

lint-all:  ## Run all linters.
	$(MAKE) black
	$(MAKE) ruff

# ===================================================================
# Fixers
# ===================================================================

fix-ruff:  ## Auto-fix ruff warnings.
	@$(call _ls,'*.py') | xargs $(PYTHON) -m ruff check --fix --output-format=concise $(ARGS)

fix-black:  ## Auto-format with black.
	@$(call _ls,'*.py') | xargs $(PYTHON) -m black

fix-all:  ## Run all fixers.
	$(MAKE) fix-ruff
	$(MAKE) fix-black

# ===================================================================
# Misc
# ===================================================================

help:  ## Display callable targets.
	@awk -F':.*?## ' '/^[a-zA-Z0-9_.-]+:.*?## / {printf "\033[36m%-24s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST) | sort
