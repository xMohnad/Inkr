lib      := pyinkr
src      := src/
run      := uv run
sync     := uv sync
build    := uv build
python   := $(run) python
ptpython := $(run) ptpython
ruff     := $(run) ruff
lint     := $(ruff) check --select I
fmt      := $(ruff) format
mypy     := $(run) mypy
spell    := $(run) codespell

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
	$(run) textual console

.PHONY: dev
dev: 					# Run in development mode with hot reload
	textual run --dev -c "$(run) $(lib)"

##############################################################################
# Setup/update packages the system requires.
.PHONY: setup
setup:				# Set up the repository for development
	$(sync)
	$(run) pre-commit install

.PHONY: update
update:				# Update all dependencies
	$(sync) --upgrade

.PHONY: resetup
resetup: realclean		# Recreate the virtual environment from scratch
	make setup

##############################################################################
# Checking/testing/linting/etc.
.PHONY: lint
lint:				# Check the code for linting issues
	$(lint) $(src) 

.PHONY: codestyle
codestyle:			# Is the code formatted correctly?
	$(fmt) --check $(src) 

.PHONY: typecheck
typecheck:			# Perform static type checks with mypy
	$(mypy) --scripts-are-modules $(src)

.PHONY: stricttypecheck
stricttypecheck:	        # Perform a strict static type checks with mypy
	$(mypy) --scripts-are-modules --strict $(src)

.PHONY: spellcheck
spellcheck:			# Spell check the code
	$(spell) *.md $(src) 

.PHONY: checkall
checkall: spellcheck codestyle lint stricttypecheck # Check all the things

##############################################################################
# Package
.PHONY: package
package:			# Package the library
	$(build)

.PHONY: spackage
spackage:			# Create a source package for the library
	$(build) --sdist

##############################################################################
# Utility.
.PHONY: repl
repl:				# Start a ptPython REPL in the venv.
	$(run) $(ptpython)

.PHONY: delint
delint:			# Fix linting issues.
	$(lint) --fix $(src)

.PHONY: pep8ify
pep8ify:			# Reformat the code to be as PEP8 as possible.
	$(fmt) $(src) 

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
