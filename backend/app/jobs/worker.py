"""One bounded execution per process. PostgreSQL enforces caps across processes."""

import argparse
import logging
import signal
import threading
from time import monotonic
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import get_engine
from app.jobs.service import JobService
from app.operations.worker import detect_page, observe


class DatabaseBreaker:
    def __init__(self, threshold=3, open_seconds=15):
        self.threshold = threshold
        self.open_seconds = open_seconds
        self.failures = 0
        self.open_until = 0.0
        self.probing = False

    def allow(self, now):
        if now < self.open_until or self.probing:
            return False
        if self.failures >= self.threshold:
            self.probing = True
        return True

    def success(self):
        self.failures = 0
        self.open_until = 0.0
        self.probing = False

    def failure(self, now):
        self.failures += 1
        self.probing = False
        if self.failures >= self.threshold:
            self.open_until = now + self.open_seconds


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    configure_logging(get_settings().log_level)
    log = logging.getLogger("northstar.worker")
    stop = threading.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: stop.set())
    service = JobService(sessionmaker(get_engine(), expire_on_commit=False))
    owner = "worker-" + uuid4().hex
    breaker = DatabaseBreaker()
    detection_at = -30.0
    tenant_cursor = None
    while not stop.is_set():
        if not breaker.allow(monotonic()):
            stop.wait(1)
            continue
        try:
            service.reconcile()
            if stop.is_set():
                break
            claim = service.claim(owner)
            if claim:
                service.process(claim, owner)
            observe(service.factory, owner)
            if monotonic() - detection_at >= 30:
                tenant_cursor = detect_page(service.factory, tenant_cursor)
                detection_at = monotonic()
            breaker.success()
            from app.jobs.metrics import snapshot

            log.info("worker_metrics", extra={"metrics": snapshot(service.factory)})
            if args.once:
                break
            if not claim:
                stop.wait(1)
        except HTTPException:
            # Cancellation/reconciliation may fence a claim between checkpoints.
            # Do not reinterpret ownership loss as permission to execute or retry.
            log.info("worker_claim_fenced", extra={"worker_id": owner})
            if args.once:
                break
        except SQLAlchemyError:
            breaker.failure(monotonic())
            log.warning("worker_database_unavailable", extra={"worker_id": owner})
            stop.wait(1)
    try:
        observe(service.factory, owner, stopped=True)
    except SQLAlchemyError:
        log.warning("worker_stop_observation_unavailable")
    get_engine().dispose()


if __name__ == "__main__":
    main()
