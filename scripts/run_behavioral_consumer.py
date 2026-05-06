"""Dev script — run the behavioral event consumer.

Reads from events.page_views, events.purchases, events.sessions.
Writes anonymized events to PostgreSQL and updates Redis profile state.

Usage:
    python scripts/run_behavioral_consumer.py
"""

import logging

from ingestion.consumers.behavioral_consumer import BehavioralEventConsumer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def main() -> None:
    consumer = BehavioralEventConsumer()
    consumer.run()


if __name__ == "__main__":
    main()
