# Local WTTJ Scheduler on WSL

The live WTTJ scrape no longer runs inside GitHub Actions.

Production execution path:
- `systemd --user` timer wakes the local scheduler
- local scheduler may start the local scrape service
- local scrape service runs the WTTJ scrape and HF upload

GitHub Actions responsibility:
- repository tests only
- no live WTTJ login
- no live parquet upload

## Install

```bash
mkdir -p ~/.config ~/.local/state/wttj-scrape ~/.config/systemd/user
cp deploy/systemd/wttj-scrape.service ~/.config/systemd/user/
cp deploy/systemd/wttj-scheduler.service ~/.config/systemd/user/
cp deploy/systemd/wttj-scheduler.timer ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now wttj-scheduler.timer
```

## Environment

Create `~/.config/wttj-scrape.env` with:

```bash
WTTJ_EMAIL=...
WTTJ_PASSWORD=...
HF_TOKEN=...
HF_DATASET_REPO=...
WTTJ_MATCHES_CONFIG=/home/seb/project/scraping_wtj/config/wttj_matches.yaml
DATA_DIR=/home/seb/project/scraping_wtj/data
WTTJ_DEBUG_DIR=/home/seb/project/scraping_wtj/artifacts/wttj-debug
WTTJ_WINDOW_START=03:30
WTTJ_WINDOW_END=05:30
WTTJ_SCHEDULER_SEED=wttj-prod
```

## Operations

```bash
# Check timer status and next wake-up
systemctl --user status wttj-scheduler.timer

# Trigger a scrape immediately (bypasses scheduler logic)
systemctl --user start wttj-scrape.service

# View scrape logs
journalctl --user -u wttj-scrape.service -n 200 --no-pager

# View scheduler decision logs
journalctl --user -u wttj-scheduler.service -n 50 --no-pager

# Check persisted state
cat ~/.local/state/wttj-scrape/state.json
```
