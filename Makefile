.PHONY: ui test lint

ui:
	cd src/cielab_gamut_tools/ui/frontend && npm run build

test:
	pytest

lint:
	ruff check src tests
	ruff format --check src tests
	mypy src
