from __future__ import annotations

import bisect
import threading
import time


class ProgressCalculator:
    # Time to calculate the speed over (in nanoseconds)
    SAMPLING_WINDOW = 1_000_000_000
    # Factor for the exponential moving average (from 0 = prev to 1 = current)
    SMOOTHING_FACTOR = 0.3

    def __init__(self, initial: int):
        self.downloaded = initial or 0

        self.elapsed: float = 0
        self.speed: int = 0
        self.eta: float | None = None

        self._total = None
        self._start_time = time.monotonic_ns()
        self._last_update = self._start_time

        self._lock = threading.Lock()
        self._thread_sizes: dict[int, int] = {}

        self._times = [self._start_time]
        self._downloaded = [self.downloaded]

    @property
    def total(self):
        return self._total

    @total.setter
    def total(self, value: int | None):
        with self._lock:
            if not value:
                value = None
            elif value < self.downloaded:
                value = self.downloaded

            self._total = value

    def thread_reset(self):
        current_thread = threading.get_ident()
        with self._lock:
            self._thread_sizes[current_thread] = 0

    def update(self, size: int | None):
        if not size:
            return

        current_thread = threading.get_ident()

        with self._lock:
            last_size = self._thread_sizes.get(current_thread, 0)
            self._thread_sizes[current_thread] = size
            self._update(size - last_size)

    def _update(self, size: int):
        current_time = time.monotonic_ns()

        self.downloaded += size
        self.elapsed = (current_time - self._start_time) / 1_000_000_000
        if self.total is not None and self.downloaded > self.total:
            self._total = self.downloaded

        self._times.append(current_time)
        self._downloaded.append(self.downloaded)

        if current_time <= self._last_update:
            return
        self._last_update = current_time

        offset = bisect.bisect_left(self._times, current_time - self.SAMPLING_WINDOW)
        del self._times[:offset]
        del self._downloaded[:offset]
        download_time = current_time - self._times[0]
        if not download_time:
            return
        downloaded_bytes = self.downloaded - self._downloaded[0]
        speed = round(downloaded_bytes * 1_000_000_000 / download_time)

        self.speed = int(self.SMOOTHING_FACTOR * speed + (1 - self.SMOOTHING_FACTOR) * self.speed)

        if not self.total:
            self.eta = None
        elif self.speed:
            self.eta = (self.total - self.downloaded) / self.speed
