# Local WTTJ Systemd Timer on WSL

The live WTTJ scrape no longer runs inside GitHub Actions.

Production execution path:
- `systemd --user` timer runs once daily with a 2h randomized delay
- missed runs are caught up when WSL starts again (`Persistent=true`)
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
ln -sf "$(pwd)/deploy/systemd/wttj-scheduler.timer" ~/.config/systemd/user/
rm -f ~/.config/systemd/user/wttj-scheduler.service
loginctl enable-linger "$USER"
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
WTTJ_AUTH_STATE_PATH=/home/seb/.local/state/wttj-scrape/auth-state.json
```

## Windows bootstrap

WSL cannot run timers while the Windows host or the WSL distro is stopped. Add
a Windows scheduled task so WSL starts after login and systemd can catch up the
missed timer:

```powershell
powershell -ExecutionPolicy Bypass -File deploy/windows/register-wsl-bootstrap.ps1 -User seb
```

## Operations

Use `make` first. The targets mirror the live systemd operations:

```bash
make wttj-scheduler-status
make wttj-status
make wttj-start
make wttj-restart
make wttj-logs
make wttj-scheduler-start
make wttj-scheduler-restart
make wttj-scheduler-logs
make wttj-refresh-auth
make wttj-state
make wttj-auth-state
```

`make wttj-refresh-auth` performs the headless login bootstrap and writes `~/.local/state/wttj-scrape/auth-state.json`. The scrape service consumes that file automatically.
