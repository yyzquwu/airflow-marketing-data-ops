.PHONY: run test clean

run:
	python scripts/run_pipeline.py

test:
	pytest

clean:
	rm -rf output .pytest_cache

