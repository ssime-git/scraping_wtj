# WTTJ Local Scheduler Design

## Goal

Replace GitHub Actions runner-based scraping with a local WSL scheduling model that runs the authenticated WTTJ scrape once per day in an early-morning randomized window, uploads refreshed data to Hugging Face, and remains easy to inspect, stop, and repair.

## Scope

This design covers:
- removal of the GitHub self-hosted runner approach for the real scrape
- local scheduling and execution on this WSL machine
- daily randomized execution in an early-morning window
- bounded execution with lock protection and clear local state
- local upload of refreshed parquet data to Hugging Face
- operational visibility through `systemd --user` and `journald`

This design does not require:
- inbound webhooks
- public endpoints
- long-running polling loops
- GitHub Actions to execute the scrape itself

## Why this design

Observed behavior is now clear:
- the authenticated WTTJ scrape works from this WSL machine when run directly
- the same scrape fails when executed inside a GitHub Actions job, even on the same machine through the self-hosted runner

The reliable boundary is therefore: local process execution works, GitHub Actions job execution does not. The design must keep the actual scrape outside GitHub Actions.

## Rejected approaches

### 1. GitHub-hosted or self-hosted Actions runner for the scrape
Rejected because the scrape behavior differs inside the Actions job context and repeatedly falls back to login or consent walls.

### 2. Public webhook into the WSL machine
Rejected because it requires network exposure, ingress hardening, and ongoing operational care for little value.

### 3. Long-running local worker loop
Rejected because it creates the exact “forgotten background process” failure mode we want to avoid.

## Recommended architecture

### Execution model

Use `systemd --user` with two units:
- `wttj-scheduler.service`: a short-lived decision step
- `wttj-scheduler.timer`: wakes up the scheduler periodically

The scheduler decides whether today’s scrape should run. If yes, it starts:
- `wttj-scrape.service`: a bounded one-shot scrape and upload job

There is no forever-loop process. Every service invocation starts, does its work, and exits.

### Scheduling model

The job should run once per calendar day, very early in the morning, but not at a fixed minute.

Recommended operating window:
- start window: `03:30`
- end window: `05:30`
- cadence of scheduler checks: every `30 minutes`

The scheduler computes one randomized target time per day inside that window. On each timer wake-up it checks:
- has a successful run already happened today?
- is a scrape already running?
- has today’s randomized target time been reached?

Only if all answers allow it, the scheduler launches the scrape.

### State model

Persist minimal state in a local file, for example:
- `/home/seb/.local/state/wttj-scrape/state.json`

State fields:
- `date`: the day the target applies to
- `target_time`: randomized run time selected for that day
- `last_started_at`
- `last_succeeded_at`
- `last_failed_at`
- `last_status`
- `last_run_id` or similar local identifier

Rules:
- one target time per day
- one successful run maximum per day
- failures do not generate repeated retries all day by default
- next day generates a fresh target time

### Concurrency control

Use a lock to prevent overlapping runs.

Recommended implementation:
- `flock` around the real scrape entrypoint
- lock file under `/home/seb/.local/state/wttj-scrape/run.lock`

If the lock is already held, the scheduler exits cleanly and logs why.

## Components

### 1. Local scrape runner

A dedicated local entrypoint runs the full pipeline:
- authenticated WTTJ scrape
- parquet merge/update
- Hugging Face upload

This runner should wrap existing scripts instead of duplicating business logic.

Expected sequence:
1. load env and config
2. run `scripts/scrape_matches_to_parquet.py`
3. if successful, run `scripts/upload_parquet_to_hf.py`
4. update local state and logs
5. exit with a clear code

### 2. Scheduler decision script

A small script decides whether to run now.

Responsibilities:
- read local state
- compute or reuse today’s randomized target time
- compare current local time to target time
- skip if already succeeded today
- skip if run currently locked
- trigger `wttj-scrape.service` when due
- write state changes

This script must do no scraping itself.

### 3. systemd units

#### `wttj-scrape.service`
A one-shot service that executes the real local pipeline.

Properties:
- bounded runtime
- explicit environment file
- no restart loop
- clear stdout/stderr into journald

#### `wttj-scheduler.service`
A one-shot service that only evaluates “should I run now?”.

#### `wttj-scheduler.timer`
A timer that wakes the scheduler every 30 minutes.

This separation makes the system easy to understand:
- timer wakes scheduler
- scheduler may start scraper
- scraper exits

## Configuration

Keep runtime configuration explicit and local.

Recommended local environment file:
- `/home/seb/.config/wttj-scrape.env`

Contents include:
- `WTTJ_EMAIL`
- `WTTJ_PASSWORD`
- `HF_TOKEN`
- `HF_DATASET_REPO`
- `WTTJ_MATCHES_CONFIG`
- `DATA_DIR`
- `WTTJ_DEBUG_DIR`

The YAML config in the repo remains the source of scrape filters and timing-related business settings where relevant. The systemd environment file holds secrets and machine-specific paths.

## Observability and operations

### Primary inspection commands
- `systemctl --user status wttj-scheduler.timer`
- `systemctl --user status wttj-scheduler.service`
- `systemctl --user status wttj-scrape.service`
- `journalctl --user -u wttj-scheduler.service`
- `journalctl --user -u wttj-scrape.service`

### Manual operations
- force a scrape now: `systemctl --user start wttj-scrape.service`
- force a scheduling decision now: `systemctl --user start wttj-scheduler.service`
- disable automation: `systemctl --user disable --now wttj-scheduler.timer`
- re-enable automation: `systemctl --user enable --now wttj-scheduler.timer`

### Logging expectations
Logs should explicitly record:
- today’s selected randomized target time
- why the scheduler skipped or launched a run
- scrape success/failure
- upload success/failure
- runtime duration

## Failure handling

### Scrape failure
If scraping fails:
- mark `last_status=failed`
- record `last_failed_at`
- preserve debug artifacts locally
- do not upload partial data
- do not retry continuously the same morning

### Upload failure
If upload fails after a successful scrape:
- keep local parquet output intact
- mark failure in state/logs distinctly
- allow manual rerun of upload or full job

### Reboot or downtime
Because the scheduler wakes every 30 minutes and computes from local state:
- a short reboot does not break the model
- if the machine comes back while still inside the daily window, the next wake-up can still run
- if the whole window is missed, the run waits for the next day

## GitHub role after redesign

GitHub remains useful for:
- versioning code
- CI for tests only
- optional documentation or status reporting

GitHub Actions should no longer be responsible for executing the live WTTJ scrape.

The existing scrape workflow should be either:
- removed as an execution path for production scraping, or
- reduced to test-only / manual support tasks

## Migration plan

1. stop and unregister the current self-hosted GitHub runner
2. remove or disable runner-specific local service files
3. remove runner-oriented workflow assumptions from the repo
4. add the local scheduler scripts and systemd units
5. add state directory and env-file conventions
6. validate manual `wttj-scrape.service` execution
7. validate scheduler decision logic with a forced test window
8. enable the daily timer

## Success criteria

The redesign is successful when:
- no GitHub runner is required for the live scrape
- no long-lived custom loop is running
- the system appears clearly in `systemctl --user`
- one scrape runs at most once per day
- the run happens in a randomized early-morning window
- the scrape and HF upload succeed when launched locally
- failures are diagnosable from journald and local state
