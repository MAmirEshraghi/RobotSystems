"""
Task wrappers for producer / consumer-producer / consumer loops.

These are intentionally small (RossROS-like), but kept in your repository so
you can run demos without pulling external code.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional, Sequence, Any, List
import time
import logging
from threading import Event

from .bus import Bus


def _sleep(dt: float) -> None:
    if dt and dt > 0:
        time.sleep(dt)


@dataclass
class TaskBase:
    name: str
    delay_s: float
    shutdown_event: Event
    termination_bus: Optional[Bus[bool]] = None

    def should_stop(self) -> bool:
        if self.shutdown_event.is_set():
            return True
        if self.termination_bus is not None:
            term = self.termination_bus.read()
            if term:
                return True
        return False


@dataclass
class Producer(TaskBase):
    output_bus: Bus[Any] = None  # type: ignore
    produce: Callable[[], Any] = None  # type: ignore
    hardware_lock: Any = None

    def run(self) -> None:
        log = logging.getLogger(self.name)
        log.info("Producer starting")
        while not self.should_stop():
            if self.hardware_lock is None:
                msg = self.produce()
            else:
                with self.hardware_lock:
                    msg = self.produce()
            self.output_bus.write(msg)
            log.debug("wrote %s -> %s", self.output_bus.name, type(msg).__name__)
            _sleep(self.delay_s)
        log.info("Producer stopping")


@dataclass
class ConsumerProducer(TaskBase):
    input_buses: Sequence[Bus[Any]] = None  # type: ignore
    output_buses: Sequence[Bus[Any]] = None  # type: ignore
    transform: Callable[..., Any] = None  # type: ignore
    hardware_lock: Any = None

    def run(self) -> None:
        log = logging.getLogger(self.name)
        log.info("ConsumerProducer starting")
        while not self.should_stop():
            inputs = [b.read() for b in self.input_buses]
            if any(v is None for v in inputs):
                _sleep(self.delay_s)
                continue

            if self.hardware_lock is None:
                out = self.transform(*inputs)
            else:
                with self.hardware_lock:
                    out = self.transform(*inputs)

            # allow single or multi output
            if len(self.output_buses) == 1:
                self.output_buses[0].write(out)
            else:
                if not isinstance(out, (list, tuple)) or len(out) != len(self.output_buses):
                    raise ValueError(
                        f"{self.name}: transform must return {len(self.output_buses)} outputs"
                    )
                for bus, msg in zip(self.output_buses, out):
                    bus.write(msg)

            log.debug("read %s wrote %s", [b.name for b in self.input_buses], [b.name for b in self.output_buses])
            _sleep(self.delay_s)
        log.info("ConsumerProducer stopping")


@dataclass
class Consumer(TaskBase):
    input_buses: Sequence[Bus[Any]] = None  # type: ignore
    consume: Callable[..., None] = None  # type: ignore
    hardware_lock: Any = None

    def run(self) -> None:
        log = logging.getLogger(self.name)
        log.info("Consumer starting")
        while not self.should_stop():
            inputs = [b.read() for b in self.input_buses]
            if any(v is None for v in inputs):
                _sleep(self.delay_s)
                continue

            if self.hardware_lock is None:
                self.consume(*inputs)
            else:
                with self.hardware_lock:
                    self.consume(*inputs)

            _sleep(self.delay_s)
        log.info("Consumer stopping")


@dataclass
class Timer(Producer):
    """Sets output_bus=True after duration_s, then keeps it True."""
    duration_s: float = 0.0
    _t0: float = 0.0

    def run(self) -> None:
        log = logging.getLogger(self.name)
        self._t0 = time.time()
        log.info("Timer starting (%.2fs)", self.duration_s)
        while not self.should_stop():
            elapsed = time.time() - self._t0
            if elapsed >= self.duration_s:
                self.output_bus.write(True)
                log.info("Timer fired; termination bus set True")
                # keep it True, but don't spam
                _sleep(max(self.delay_s, 0.5))
            else:
                self.output_bus.write(False)
                _sleep(self.delay_s if self.delay_s > 0 else 0.05)
        log.info("Timer stopping")
