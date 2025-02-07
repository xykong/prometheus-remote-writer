.PHONY: all proto clean
VENV := .venv/bin

all: proto

proto:
	@echo "Generating Python files from proto..."
	$(VENV)/python ./proto/generate-proto.py


clean:
	@echo "Cleaning up generated files..."
	rm -f prometheus_remote_writer/proto/*.py
	find . \( -name '*.pyc' -o -name '__pycache__' \) -exec rm -rf {} +


test:
	$(VENV)/pytest tests/


lint:
	@echo "Running linter..."
	$(VENV)/flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
	$(VENV)/flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics


check: clean proto lint test
	$(VENV)/tox
	@echo "\nAll checks passed!"
