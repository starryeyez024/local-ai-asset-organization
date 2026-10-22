.PHONY: help regen serve run

PYTHON ?= python3
EXPLORER_DIR ?= $(HOME)/.local/share/ai-assets-explorer
CONFIG ?=
PORT ?=

help:
	@echo "AI Asset Explorer -- available commands:"
	@echo ""
	@echo "  make regen   Prepare or refresh your local Explorer and catalog"
	@echo "  make serve   Serve the site locally on the saved port (default 8980)"
	@echo "  make run     Regenerate then serve (the usual 'just run it' command)"
	@echo ""
	@echo "Select configuration: make run CONFIG=/path/to/agent-config.toml"
	@echo "Select local output: make run EXPLORER_DIR=/path/to/local/explorer"
	@echo "Select local port: make run PORT=8990"

regen:
	$(PYTHON) -B ../skills/agent-setup/scripts/prepare-explorer.py $(if $(CONFIG),--config "$(CONFIG)",) --output-dir "$(EXPLORER_DIR)" $(if $(PORT),--port "$(PORT)",)

serve:
	$(PYTHON) -B "$(EXPLORER_DIR)/serve.py"

run: regen
	$(MAKE) serve
