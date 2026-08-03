import unittest
from unittest.mock import patch

import requests

from handlers import rss


RSS_BODY = b'<?xml version="1.0"?><rss><channel><item><title>News</title></item></channel></rss>'


class FakeResponse:
    def __init__(self, status=200, body=RSS_BODY, content_type="application/rss+xml", location=None):
        self.status_code = status
        self.body = body
        self.headers = {"Content-Type": content_type}
        if location:
            self.headers["Location"] = location
        self.is_redirect = status in {301, 302, 303, 307}
        self.is_permanent_redirect = status == 308
        self.closed = False

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}", response=self)

    def iter_content(self, chunk_size=64 * 1024):
        for index in range(0, len(self.body), chunk_size):
            yield self.body[index:index + chunk_size]

    def close(self):
        self.closed = True


class RSSFetchTests(unittest.TestCase):
    def setUp(self):
        rss._clear_rss_cache_for_tests()

    def test_rejects_unapproved_host_before_request(self):
        with patch.object(rss.requests, "get") as get:
            with self.assertRaises(rss.RSSFetchError) as caught:
                rss.fetch_rss_feed("http://127.0.0.1:3001/api/health")
        self.assertEqual(caught.exception.status, 400)
        get.assert_not_called()

    def test_success_is_cached(self):
        with patch.object(rss.requests, "get", return_value=FakeResponse()) as get:
            first = rss.fetch_rss_feed("https://cointelegraph.com/rss")
            second = rss.fetch_rss_feed("https://cointelegraph.com/rss")

        self.assertEqual(first.cache_status, "miss")
        self.assertEqual(second.cache_status, "hit")
        self.assertEqual(second.body, RSS_BODY)
        self.assertEqual(get.call_count, 1)

    def test_uses_fallback_when_publisher_returns_403(self):
        responses = [FakeResponse(status=403, body=b"blocked"), FakeResponse()]
        with patch.object(rss.requests, "get", side_effect=responses) as get:
            result = rss.fetch_rss_feed("https://www.theblock.co/rss.xml")

        self.assertTrue(result.used_fallback)
        self.assertEqual(result.body, RSS_BODY)
        self.assertEqual(get.call_count, 2)
        self.assertIn("news.google.com", get.call_args_list[1].args[0])

    def test_every_vps_blocked_publisher_has_a_recent_fallback(self):
        self.assertIn("https://www.theblock.co/rss.xml", rss.FEED_FALLBACKS)
        self.assertIn("https://blockworks.co/feed/", rss.FEED_FALLBACKS)
        self.assertIn("https://cryptoslate.com/feed/", rss.FEED_FALLBACKS)
        self.assertIn("when%3A7d", rss.FEED_FALLBACKS["https://cryptoslate.com/feed/"])

    def test_converts_chainlink_blog_page_to_rss(self):
        redirect = FakeResponse(status=301, location="https://chain.link/blog")
        page = FakeResponse(
            body=(
                b'<html><a href="/blog/example-story" class="media-card w-inline-block">'
                b'<h3>Official &amp; Current</h3></a></html>'
            ),
            content_type="text/html",
        )
        with patch.object(rss.requests, "get", side_effect=[redirect, page]):
            result = rss.fetch_rss_feed("https://blog.chain.link/rss/")

        self.assertFalse(result.used_fallback)
        self.assertIn(b"Official &amp; Current", result.body)
        self.assertIn(b"https://chain.link/blog/example-story", result.body)

    def test_serves_last_good_feed_during_temporary_outage(self):
        with patch.object(rss.requests, "get", return_value=FakeResponse()):
            rss.fetch_rss_feed("https://cointelegraph.com/rss")

        with (
            patch.object(rss, "FRESH_CACHE_SECONDS", -1),
            patch.object(rss, "_download_with_retry", side_effect=rss.RSSFetchError("offline")),
        ):
            result = rss.fetch_rss_feed("https://cointelegraph.com/rss")

        self.assertEqual(result.cache_status, "stale")
        self.assertEqual(result.body, RSS_BODY)

    def test_redirect_to_unapproved_host_is_blocked(self):
        response = FakeResponse(status=302, location="http://localhost:3001/api/health")
        with patch.object(rss.requests, "get", return_value=response):
            with self.assertRaises(rss.RSSFetchError) as caught:
                rss.fetch_rss_feed("https://cointelegraph.com/rss")

        self.assertIn("approved", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
