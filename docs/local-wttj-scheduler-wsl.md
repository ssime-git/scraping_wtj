# Local WTTJ Scheduler on WSL

The live WTTJ scrape no longer runs inside GitHub Actions.

Production execution path:
- `systemd --user` timer wakes the local scheduler every 30 min
- local scheduler decides whether today's scrape is due
- local scrape service runs the WTTJ scrape and HF upload

GitHub Actions responsibility:
- repository tests only
- no live WTTJ login
- no live parquet upload

## Install

Symlinks keep unit files in sync with the repo — after a `git pull` that modifies them, only `daemon-reload` is needed.

```bash
mkdir -p ~/.config/systemd/user ~/.local/state/wttj-scrape
ln -sf "$(pwd)/deploy/systemd/wttj-scrape.service" ~/.config/systemd/user/
ln -sf "$(pwd)/deploy/systemd/wttj-scheduler.service" ~/.config/systemd/user/
ln -sf "$(pwd)/deploy/systemd/wttj-scheduler.timer" ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now wttj-scheduler.timer
```

After any `git pull` that touches `deploy/systemd/`:

```bash
systemctl --user daemon-reload
```

## Environment

Create `~/.config/wttj-scrape.env`:

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

# Follow scrape logs live
journalctl --user -u wttj-scrape.service -f

# View scheduler decision logs
journalctl --user -u wttj-scheduler.service -n 50 --no-pager

# Check persisted state
cat ~/.local/state/wttj-scrape/state.json
```
