VERSION = 0.1.0

.PHONY: test coverage lint format clean

test:
	python -m pytest tests/ -v

coverage:
	python -m pytest tests/ --cov=voxkit --cov-report=term-missing --cov-report=lcov:coverage.lcov

lint:
	ruff check src/ tests/
	ruff format --check src/ tests/

format:
	ruff format src/ tests/
	ruff check --fix src/ tests/

clean:
	rm -rf build/ dist/ *.egg-info src/*.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +

publish: clean
	python -m build
	python -m twine upload dist/*

publish-test: clean
	python -m build
	python -m twine upload --repository testpypi dist/*
