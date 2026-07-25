lib              := pyinkr
exec             := inkr
src              := src/

RUFF         ?= uvx ruff
BASEDPYRIGHT ?= uvx basedpyright
CODESPELL    ?= uvx codespell
PYTHON       ?= uv run python

##@ Development

.PHONY: run
run:				# Run the code in a testing context
	$(PYTHON) -m $(lib)

.PHONY: console
console:			# Run the textual console
	uv run textual console

.PHONY: dev
dev:				# Run in development mode with hot reload
	uv run textual run --dev -c "$(exec)"

.PHONY: setup
setup:				# Set up the repository for development
	uv venv --allow-existing
	uv sync

##@ Checking

.PHONY: lint
lint:				# Check the code for linting issues
	$(RUFF) check $(src)

.PHONY: codestyle
codestyle:			# Is the code formatted correctly?
	$(RUFF) format --check $(src)

.PHONY: typecheck
typecheck:			# Perform static type checks with basedpyright
	$(BASEDPYRIGHT) $(src)

.PHONY: spellcheck
spellcheck:			# Spell check the code
	$(CODESPELL) *.md $(src)

.PHONY: checkall
checkall: spellcheck codestyle lint typecheck	# Check all the things

##@ Utility

.PHONY: delint
delint:				# Fix linting issues.
	$(RUFF) check --fix $(src)

.PHONY: pep8ify
pep8ify:			# Reformat the code to be as PEP8 as possible.
	$(RUFF) format $(src)

.PHONY: tidy
tidy: delint pep8ify		# Tidy up the code, fixing lint and format issues.

.PHONY: clean
clean:				# Clean the package building files
	rm -rf dist/ build/ $(src)*.egg-info .pytest_cache .ruff_cache
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete

.PHONY: help
help:				# Display this help
	@awk 'BEGIN {FS = ":.+# "} \
		/^[a-zA-Z_-]+:.+# / {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2} \
		/^##@/ {printf "\n\033[1m%s\033[0m\n", substr($$0, 5)}' $(MAKEFILE_LIST)
