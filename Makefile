.PHONY: install install-live install-mcp test coverage lint format typecheck demo \
        evolve benchmark adversarial launch-check clean help

PY ?= python

help:
	@echo "Forensic LLM Wiki — common tasks"
	@echo ""
	@echo "  make install        Install runtime + dev dependencies (editable)."
	@echo "  make install-live   Same, plus the optional anthropic SDK for live mode."
	@echo "  make install-mcp    Same, plus the optional mcp SDK for the MCP server."
	@echo "  make test           Run the test suite (mock mode, no API key needed)."
	@echo "  make coverage       Run the test suite with a coverage report (85% floor)."
	@echo "  make lint           Ruff check the codebase."
	@echo "  make typecheck      Mypy the codebase."
	@echo "  make format         Ruff format the codebase."
	@echo "  make demo           Run examples/demo_commands.sh end-to-end."
	@echo "  make evolve         Run the evolving case from clean state."
	@echo "  make benchmark      Run the four-way RAG vs GraphRAG-lite vs Wiki vs Hybrid scorecard."
	@echo "  make adversarial    Run the adversarial-overclaim case benchmark."
	@echo "  make launch-check   pytest + ruff check + python fw.py --help (the DoD gate)."
	@echo "  make clean          Remove generated wiki / snapshots / benchmark / caches."

install:
	$(PY) -m pip install -e ".[dev]"

install-live:
	$(PY) -m pip install -e ".[dev,live]"

install-mcp:
	$(PY) -m pip install -e ".[dev,mcp]"

test:
	$(PY) -m pytest

coverage:
	$(PY) -m pytest --cov --cov-report=term --cov-fail-under=85

lint:
	$(PY) -m ruff check .

typecheck:
	$(PY) -m mypy

format:
	$(PY) -m ruff format .

demo:
	bash examples/demo_commands.sh

evolve:
	$(PY) fw.py evolve case_002_evolving

benchmark:
	$(PY) fw.py benchmark-methods case_002_evolving

adversarial:
	$(PY) fw.py ingest raw_sources/case_003_adversarial_overclaim --apply
	$(PY) fw.py benchmark case_003_adversarial_overclaim

launch-check:
	$(PY) -m pytest --cov --cov-report=term --cov-fail-under=85
	$(PY) -m ruff check .
	$(PY) -m mypy
	$(PY) fw.py --help > /dev/null
	@echo "launch-check: OK"

clean:
	rm -rf wiki wiki_snapshots benchmark_results
	rm -rf .pytest_cache .ruff_cache
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
