VERSION = 0.1.0

.PHONY: all publish publish-test version test coverage lint format clean

all: version

publish: version clean
	python -m build
	python -m twine upload dist/*

publish-test: version clean
	python -m build
	python -m twine upload --repository testpypi dist/*

version:
	sed -i 's/^version = "[0-9]\+\.[0-9]\+\.[0-9]\+"/version = "$(VERSION)"/' pyproject.toml
	sed -i 's/__version__ = "[0-9]\+\.[0-9]\+\.[0-9]\+"/__version__ = "$(VERSION)"/' src/voxkit/__init__.py
	sed -i 's|pip-[0-9]\+\.[0-9]\+\.[0-9]\+-blue|pip-$(VERSION)-blue|' README.md

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
