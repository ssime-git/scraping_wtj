import argparse
import asyncio

from wttj_scraper import scrape

_DEFAULT_URL = "https://www.welcometothejungle.com/fr/jobs"
_DEFAULT_MAX_JOBS = 30
_DEFAULT_ENRICH_COUNT = 15


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scrape public job offers from Welcome to the Jungle")
    parser.add_argument("--url", default=_DEFAULT_URL, help="Jobs listing URL")
    parser.add_argument("--max-jobs", type=int, default=_DEFAULT_MAX_JOBS, help="Max jobs to extract from listing")
    parser.add_argument("--enrich-count", type=int, default=_DEFAULT_ENRICH_COUNT, help="Max jobs to enrich with detail page")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)
    result = asyncio.run(scrape(args.url, args.max_jobs, args.enrich_count))
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
