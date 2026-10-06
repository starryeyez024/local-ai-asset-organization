.PHONY: help regen serve run

PORT ?= 8790

help:
	@echo "Skills Explorer -- available commands:"
	@echo ""
	@echo "  make regen   Regenerate skills.json from ~/.agents/skills (or \$$SKILLS_ROOT)"
	@echo "  make serve   Serve the site locally at http://localhost:$(PORT)"
	@echo "  make run     Regenerate then serve (the usual 'just run it' command)"
	@echo ""
	@echo "Override the port: make serve PORT=8080"
	@echo "Override the skills source: SKILLS_ROOT=/some/path make regen"

regen:
	python3 generate-skills-json.py

serve:
	@echo "Serving at http://localhost:$(PORT) -- press Ctrl+C to stop"
	python3 serve.py $(PORT)

run: regen serve
