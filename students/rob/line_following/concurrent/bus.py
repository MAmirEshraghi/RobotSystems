"""
Lightweight concurrency utilities for ROB515 line-following demos.

Implements a broadcast message bus (read does NOT clear) with optional
writer-priority read/write locking via readerwriterlock, as recommended
in the course manual.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Optional, TypeVar
import threading
import logging

T = TypeVar("T")


class Bus(Generic[T]):
    """Broadcast message bus shared across threads.

    - write(msg): atomically replaces the bus message
    - read(): atomically returns the most recent message (does not clear it)

    If readerwriterlock is installed, uses a writer-priority RW lock.
    Otherwise falls back to a normal mutex.
    """

    def __init__(self, name: str, initial: Optional[T] = None):
        self.name = str(name)
        self._message: Optional[T] = initial

        self._rw = None
        try:
            from readerwriterlock import rwlock  # type: ignore
            self._rw = rwlock.RWLockWriteD()
        except Exception:
            self._rw = None
            self._lock = threading.RLock()

    def write(self, message: Optional[T]) -> None:
        if self._rw is not None:
            with self._rw.gen_wlock():
                self._message = message
        else:
            with self._lock:
                self._message = message

    def read(self) -> Optional[T]:
        if self._rw is not None:
            with self._rw.gen_rlock():
                return self._message
        else:
            with self._lock:
                return self._message

    def __repr__(self) -> str:
        return f"Bus(name={self.name!r}, message={self._message!r})"


@dataclass
class HardwareLock:
    """Single lock to serialize I2C-heavy operations (sensor reads + motor/servo writes)."""
    lock: threading.RLock = threading.RLock()

    def __enter__(self):
        self.lock.acquire()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.lock.release()
        return False
