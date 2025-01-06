import unittest
import time
from collections import deque
from unittest.mock import patch

from arxplorer.common.limiter import RateLimiter


class TestRateLimiter(unittest.TestCase):

    def setUp(self):
        self.rate_limiter = RateLimiter(max_tokens=3, time_in_seconds=1)

    def test_init(self):
        self.assertEqual(self.rate_limiter._max_tokens, 3)
        self.assertEqual(self.rate_limiter._time_in_seconds, 1)
        self.assertIsInstance(self.rate_limiter._queue, deque)
        self.assertEqual(len(self.rate_limiter._queue), 0)

    def test_get_token_within_limit(self):
        start_time = time.time()
        for _ in range(3):
            self.rate_limiter.get_token()
        end_time = time.time()
        self.assertLess(end_time - start_time, 0.1)  # Should complete quickly

    def test_get_token_within_limit_multiple_spans(self):
        start_time = time.time()
        for _ in range(9):
            self.rate_limiter.get_token()
        end_time = time.time()
        self.assertGreater(end_time - start_time, 2)
        self.assertLess(end_time - start_time, 2.5)

    def test_get_token_exceeds_limit(self):
        start_time = time.time()
        for _ in range(4):
            self.rate_limiter.get_token()
        end_time = time.time()
        self.assertGreater(end_time - start_time, 0.9)  # Should take about 1 second

    @patch("time.time")
    def test_token_expiration(self, mock_time):
        mock_time.return_value = 100  # Set initial time
        for _ in range(3):
            self.rate_limiter.get_token()

        self.assertEqual(len(self.rate_limiter._queue), 3)

        mock_time.return_value = 101.1  # Advance time by slightly more than 1 second
        self.rate_limiter.get_token()  # This should clear expired tokens

        self.assertEqual(len(self.rate_limiter._queue), 1)

    def test_threading_safety(self):
        import threading

        def worker():
            for _ in range(9):
                self.rate_limiter.get_token()

        threads = [threading.Thread(target=worker) for _ in range(5)]
        start_time = time.time()
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        end_time = time.time()

        self.assertGreater(end_time - start_time, 14)  # Should take about 14 seconds
        self.assertLess(
            end_time - start_time, 16
        )  # But less than 15 seconds. It keeps failing on Mac because 15 is to strict, extending to 15.5


if __name__ == "__main__":
    unittest.main()
