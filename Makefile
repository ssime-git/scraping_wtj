WTTJ_SCHEDULER_TIMER ?= wttj-scheduler.timer
WTTJ_SCHEDULER_SERVICE ?= wttj-scheduler.service
WTTJ_SCRAPE_SERVICE ?= wttj-scrape.service

.DEFAULT_GOAL := help

.PHONY: help hc-start hc-setup \
	wttj-status wttj-restart wttj-reset-failed wttj-start wttj-logs wttj-state \
	wttj-scheduler-status wttj-scheduler-start wttj-scheduler-restart wttj-scheduler-logs \
	wttj-refresh-auth wttj-auth-state wttj-check wttj-last-logs

help:
	@printf '%s\n' "Available targets:"
	@printf '%s\n' "  make hc-start               - start healthchecks.io (http://localhost:8000)"
	@printf '%s\n' "  make hc-setup               - print post-start setup instructions"
	@printf '%s\n' "  make wttj-check             - health check: last run status, saved_jobs, any errors"
	@printf '%s\n' "  make wttj-last-logs         - full output of the last scrape run"
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

hc-start:
	docker compose up -d healthchecks
	@echo "Healthchecks running at http://localhost:8000"

hc-setup:
	@echo "1. Open http://localhost:8000 and create an account"
	@echo "2. Create a check: Cron schedule '46 3 * * *', grace 2h"
	@echo "3. Copy the ping URL (e.g. http://localhost:8000/ping/<uuid>)"
	@echo "4. Set it in ~/.config/wttj-scrape.env:"
	@echo "   HC_PING_URL=http://localhost:8000/ping/<uuid>"

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

wttj-check:
	@echo "=== Last run state ==="
	@cat ~/.local/state/wttj-scrape/state.json | python3 -c "\
import json,sys; s=json.load(sys.stdin); \
print(f\"  date:         {s.get('date')}\"); \
print(f\"  status:       {s.get('last_status')}\"); \
print(f\"  started:      {s.get('last_started_at')}\"); \
print(f\"  succeeded:    {s.get('last_succeeded_at')}\"); \
print(f\"  failed:       {s.get('last_failed_at')}\"); \
"
	@echo ""
	@echo "=== Last 5 scrape outcomes ==="
	@journalctl --user -u $(WTTJ_SCRAPE_SERVICE) --no-pager -o cat -n 500 \
		| grep -E "saved_jobs|Pushed to HF|RuntimeError|Error|Traceback" | tail -10
	@echo ""
	@echo "=== Errors in recent logs ==="
	@journalctl --user -u $(WTTJ_SCRAPE_SERVICE) --no-pager -o cat -n 200 \
		| grep -E "Error|Traceback|CRITICAL|RuntimeError" | tail -10 || echo "  (none)"

wttj-last-logs:
	@journalctl --user -u $(WTTJ_SCRAPE_SERVICE) --no-pager -o cat -n 200 \
		| grep -E --color=always "Error|Traceback|CRITICAL|WARNING|saved_jobs|Pushed|families|$$" | less -R
