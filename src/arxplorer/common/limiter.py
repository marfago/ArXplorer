import random
import threading
import time
from collections import deque
from time import sleep


class RateLimiter:
    def __init__(self, max_tokens: int = 15, time_in_seconds: float = 60):
        self._max_tokens = max_tokens
        self._time_in_seconds = time_in_seconds
        self._queue = deque()
        self._lock = threading.Lock()

    def get_token(self):
        with self._lock:
            while True:
                while self._queue and (time.time() - self._queue[0]) >= self._time_in_seconds:
                    self._queue.popleft()
                if len(self._queue) < self._max_tokens:
                    self._queue.append(time.time())
                    return
                sl = self._time_in_seconds - (time.time() - self._queue[0])
                time.sleep(sl)


if __name__ == "__main__":  # pragma: no cover
    rl = RateLimiter(10, 10)
    while True:
        rl.get_token()
        print(time.time())
        sleep(random.random())
