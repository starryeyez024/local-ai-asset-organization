.PHONY: help regen serve run

PORT ?= 8790
PYTHON ?= python3
EXPLORER_DIR ?= $(HOME)/.local/share/ai-assets-explorer
CONFIG ?=

help:
	@echo "AI Asset Explorer -- available commands:"
	@echo ""
	@echo "  make regen   Prepare or refresh your local Explorer and catalog"
	@echo "  make serve   Serve the site locally at http://localhost:$(PORT)"
	@echo "  make run     Regenerate then serve (the usual 'just run it' command)"
	@echo ""
	@echo "Override the port: make serve PORT=8080"
	@echo "Select configuration: make run CONFIG=/path/to/agent-config.toml"
	@echo "Select local output: make run EXPLORER_DIR=/path/to/local/explorer"

regen:
	$(PYTHON) -B ../skills/agent-setup/scripts/prepare-explorer.py $(if $(CONFIG),--config "$(CONFIG)",) --output-dir "$(EXPLORER_DIR)"

serve:
	@echo "Serving at http://localhost:$(PORT) -- press Ctrl+C to stop"
	$(PYTHON) -B "$(EXPLORER_DIR)/serve.py" $(PORT)

run: regen
	$(MAKE) serve
