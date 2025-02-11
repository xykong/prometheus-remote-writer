.PHONY: all proto clean
VENV := .venv/bin

all: proto

proto:
	@echo "Generating Python files from proto..."
	$(VENV)/python ./proto/generate-proto.py


clean:
	@echo "Cleaning up generated files..."
	rm -rf .tox
	rm -rf .pytest_cache
	rm -rf .poetry
	rm -rf .venv
	rm -rf dist
	-rm .DS_Store
	find . \( -name '*.pyc' -o -name '__pycache__' \) -exec rm -rf {} +


test: proto
	$(VENV)/pytest tests/


lint: proto
	@echo "Running linter..."
	$(VENV)/flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
	$(VENV)/flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics


check: clean lint test
	$(VENV)/tox
	@echo "\nAll checks passed!"


publish: check
	@echo "Publishing to PyPI..."
	poetry publish --build


bump = patch
next-version = $(shell poetry version $(bump) -s --dry-run)
release:
	@echo "Creating a new release..."
	git flow release start $(next-version)
	poetry version $(bump)
	GIT_MERGE_AUTOEDIT=no git flow release finish -m "publish"
	git push --all
	git push --tags
