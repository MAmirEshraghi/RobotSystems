"""
ThreadPoolExecutor runner with graceful shutdown + exception reporting.

The manual notes Ctrl+C + concurrent.futures needs special care, and that
exceptions in child threads may not show up unless you capture them.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence, Callable
import time
import logging
from concurrent.futures import ThreadPoolExecutor, Future
from threading import Event


def _handle_exception(fut: Future) -> None:
    exc = fut.exception()
    if exc is not None:
        logging.getLogger("runner").exception("Exception in worker thread", exc_info=exc)


@dataclass
class ConcurrentRunner:
    tasks: Sequence[Callable[[], None]]
    shutdown_event: Event
    max_workers: int

    def run(self) -> None:
        log = logging.getLogger("runner")
        futures: List[Future] = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as ex:
            for t in self.tasks:
                fut = ex.submit(t)
                fut.add_done_callback(_handle_exception)
                futures.append(fut)

            try:
                # Keep the main thread alive for Ctrl+C
                while not self.shutdown_event.is_set():
                    time.sleep(0.2)
            except KeyboardInterrupt:
                log.info("KeyboardInterrupt: shutting down")
                self.shutdown_event.set()
            finally:
                ex.shutdown(wait=True)
                log.info("All threads joined")
