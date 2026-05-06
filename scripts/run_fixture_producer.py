"""Dev script — run the fixture event producer to populate Kafka topics.

Usage:
    python scripts/run_fixture_producer.py
    python scripts/run_fixture_producer.py --page-views 100 --purchases 20 --sessions 30
"""

import argparse
import logging

from ingestion.producers.fixture_producer import FixtureEventProducer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def main() -> None:
    parser = argparse.ArgumentParser(description="Produce synthetic behavioral events to Kafka.")
    parser.add_argument("--page-views", type=int, default=20, help="Number of page view events")
    parser.add_argument("--purchases",  type=int, default=5,  help="Number of purchase events")
    parser.add_argument("--sessions",   type=int, default=10, help="Number of session pairs (start+end)")
    args = parser.parse_args()

    producer = FixtureEventProducer()
    try:
        producer.produce_batch(
            n_page_views=args.page_views,
            n_purchases=args.purchases,
            n_sessions=args.sessions,
        )
    finally:
        producer.close()


if __name__ == "__main__":
    main()
