# Self-Hosted Runner on WSL

This repository now expects the scrape workflow to run on a self-hosted runner with labels:

- `self-hosted`
- `linux`
- `x64`
- `wttj`

## Why

The authenticated WTTJ scrape is stable on this WSL machine but not on GitHub-hosted runners. The workflow was switched to a self-hosted runner so the real scrape executes from the same environment that already works locally.

## Prerequisites on the machine

- WSL with outbound internet access
- `git`
- `curl`
- `tar`
- Python 3.12+
- `uv`
- Playwright system dependencies already installed locally

## Register the runner

From this machine:

1. Create a folder for the runner, for example `~/github-runner/wttj`
2. Download the GitHub Actions runner
3. Generate a repo runner registration token
4. Configure the runner with label `wttj`
5. Start it

## Example commands

Replace the runner version if needed.

```bash
mkdir -p ~/github-runner/wttj
cd ~/github-runner/wttj

curl -L -o actions-runner-linux-x64-2.319.1.tar.gz \
  https://github.com/actions/runner/releases/download/v2.319.1/actions-runner-linux-x64-2.319.1.tar.gz

tar xzf actions-runner-linux-x64-2.319.1.tar.gz
```

Generate a registration token:

```bash
gh api \
  --method POST \
  repos/ssime-git/scraping_wtj/actions/runners/registration-token \
  --jq .token
```

Configure the runner:

```bash
./config.sh \
  --url https://github.com/ssime-git/scraping_wtj \
  --token <TOKEN> \
  --labels wttj \
  --name wttj-wsl \
  --unattended
```

Start the runner:

```bash
./run.sh
```

## Recommended operational mode

- Keep the runner inside a dedicated shell/session
- Do not run multiple WTTJ scrapes concurrently
- Leave the workflow `concurrency` guard enabled

## Optional service mode

If systemd is available in WSL, you can install the runner as a service:

```bash
sudo ./svc.sh install
sudo ./svc.sh start
```

## Validation

After the runner is online:

- open the repository settings on GitHub
- confirm the runner appears with label `wttj`
- trigger `Scrape WTTJ` via `workflow_dispatch`
