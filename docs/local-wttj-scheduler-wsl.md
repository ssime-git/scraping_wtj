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
