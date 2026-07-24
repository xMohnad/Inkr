lib              := pyinkr
exec             := inkr
src              := src/

##############################################################################
# Local "interactive testing" of the code.
.PHONY: run
run:				# Run the code in a testing context
	$(python) -m $(lib)

.PHONY: debug
debug:				# Run the code with Textual devtools enabled
	TEXTUAL=devtools make

.PHONY: console
console:			# Run the textual console
	textual console

.PHONY: dev
dev: 					# Run in development mode with hot reload
	textual run --dev -c "$(exec)"

##############################################################################
# Setup/update packages the system requires.
.PHONY: setup
setup:				# Set up the repository for development
	uv venv --allow-existing
	uv sync

.PHONY: update
update:				# Update all dependencies
	uv sync --upgrade

.PHONY: resetup
resetup: realclean		# Recreate the virtual environment from scratch
	make setup

##############################################################################
# Checking/testing/linting/etc.
.PHONY: lint
lint:				# Check the code for linting issues
	ruff check $(src)

.PHONY: codestyle
codestyle:			# Is the code formatted correctly?
	ruff format --check $(src)

.PHONY: typecheck
typecheck:			# Perform static type checks with basedpyright
	basedpyright $(src)

.PHONY: spellcheck
spellcheck:			# Spell check the code
	 codespell *.md $(src)

.PHONY: checkall
checkall: spellcheck codestyle lint typecheck # Check all the things

##############################################################################
# Package
.PHONY: package
package:			# Package the library
	uv build

.PHONY: spackage
spackage:			# Create a source package for the library
	uv build --sdist

##############################################################################
# Utility.
.PHONY: repl
repl:				# Start a ptPython REPL in the venv.
	$(ptpython)

.PHONY: delint
delint:			# Fix linting issues.
	ruff check --fix $(src)

.PHONY: pep8ify
pep8ify:			# Reformat the code to be as PEP8 as possible.
	ruff format $(src)

.PHONY: tidy
tidy: delint pep8ify		# Tidy up the code, fixing lint and format issues.

.PHONY: clean
clean:		# Clean the package building files
	rm -rf dist/ build/ $(src)*.egg-info .pytest_cache
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete

.PHONY: realclean
realclean: clean		# Clean the venv and build directories
	rm -rf .venv

.PHONY: help
help:				# Display this help
	@grep -Eh "^[a-z]+:.+# " $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.+# "}; {printf "%-20s %s\n", $$1, $$2}'
