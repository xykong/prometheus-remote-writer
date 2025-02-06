.PHONY: all proto clean

all: proto

proto:
	@echo "Generating Python files from proto..."
	cd proto && uv run generate-proto.py


clean:
	@echo "Cleaning up generated files..."
	rm -f src/prometheus_remote_writer/*.py
	rm -f src/prometheus_remote_writer/*.pyc
	rm -rf src/prometheus_remote_writer/__pycache__


test:
	PYTHONPATH=./src uv run pytest tests/
