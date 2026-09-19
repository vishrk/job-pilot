"""Polls for due Hunts and runs them. Run alongside the API: python -m app.worker"""

import logging
import time

from app.db import SessionLocal
from app.services.hunt_runner import run_due_hunts

logging.basicConfig(level=logging.INFO)
POLL_SECONDS = 60


def main():
    while True:
        db = SessionLocal()
        try:
            n = run_due_hunts(db)
            if n:
                logging.info("ran %d due hunt(s)", n)
        finally:
            db.close()
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
