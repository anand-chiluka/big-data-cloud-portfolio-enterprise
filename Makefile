.PHONY: data test lint clean

data:
	python data/generators/generate_sample_data.py

test:
	pytest -q

lint:
	python -m compileall shared projects tests

clean:
	find . -name "__pycache__" -type d -prune -exec rm -rf {} +
	find . -name "*.pyc" -delete
