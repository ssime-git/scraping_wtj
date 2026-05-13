WTTJ_SCHEDULER_TIMER ?= wttj-scheduler.timer
WTTJ_SCHEDULER_SERVICE ?= wttj-scheduler.service
WTTJ_SCRAPE_SERVICE ?= wttj-scrape.service

.DEFAULT_GOAL := help

.PHONY: help wttj-status wttj-restart wttj-reset-failed wttj-start wttj-logs wttj-state \
	wttj-scheduler-status wttj-scheduler-start wttj-scheduler-restart wttj-scheduler-logs \
	wttj-refresh-auth wttj-auth-state

help:
	@printf '%s\n' "Available targets:"
	@printf '%s\n' "  make wttj-status            - show scrape service status"
	@printf '%s\n' "  make wttj-restart           - reset-failed, start, and show scrape status"
	@printf '%s\n' "  make wttj-reset-failed      - clear the scrape service failure state"
	@printf '%s\n' "  make wttj-start             - start the scrape service"
	@printf '%s\n' "  make wttj-logs              - follow scrape service logs"
	@printf '%s\n' "  make wttj-state             - print persisted scrape state"
	@printf '%s\n' "  make wttj-scheduler-status  - show scheduler timer status"
	@printf '%s\n' "  make wttj-scheduler-start   - start the scheduler service now"
	@printf '%s\n' "  make wttj-scheduler-restart - restart the scheduler service now"
	@printf '%s\n' "  make wttj-scheduler-logs    - follow scheduler service logs"
	@printf '%s\n' "  make wttj-refresh-auth      - refresh the headless WTTJ auth state"
	@printf '%s\n' "  make wttj-auth-state        - print persisted auth state path"

wttj-status:
	systemctl --user status $(WTTJ_SCRAPE_SERVICE) --no-pager

wttj-restart:
	systemctl --user reset-failed $(WTTJ_SCRAPE_SERVICE)
	systemctl --user start $(WTTJ_SCRAPE_SERVICE)
	systemctl --user status $(WTTJ_SCRAPE_SERVICE) --no-pager

wttj-reset-failed:
	systemctl --user reset-failed $(WTTJ_SCRAPE_SERVICE)

wttj-start:
	systemctl --user start $(WTTJ_SCRAPE_SERVICE)

wttj-logs:
	journalctl --user -u $(WTTJ_SCRAPE_SERVICE) -f

wttj-state:
	cat ~/.local/state/wttj-scrape/state.json

wttj-scheduler-status:
	systemctl --user status $(WTTJ_SCHEDULER_TIMER) --no-pager

wttj-scheduler-start:
	systemctl --user start $(WTTJ_SCHEDULER_SERVICE)

wttj-scheduler-restart:
	systemctl --user restart $(WTTJ_SCHEDULER_SERVICE)

wttj-scheduler-logs:
	journalctl --user -u $(WTTJ_SCHEDULER_SERVICE) -f

wttj-refresh-auth:
	set -a; . ~/.config/wttj-scrape.env; set +a; /home/seb/.local/bin/uv run python scripts/refresh_wttj_auth.py

wttj-auth-state:
	stat -c '%y %n' ~/.local/state/wttj-scrape/auth-state.json
