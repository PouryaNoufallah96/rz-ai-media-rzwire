import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from telegram_public import (
    filter_posts_by_hours,
    normalize_channel,
    parse_telegram_public_html,
    parse_view_count,
    rank_by_keyword_match,
    rank_telegram_posts,
    strip_leading_editorial_label,
)


SAMPLE_HTML = """
<html><body>
  <div class="tgme_widget_message text_not_supported_wrap js-widget_message" data-post="cointelegraph/12345">
    <div class="tgme_widget_message_text js-message_text" dir="auto">
      Bitcoin ETFs saw fresh inflows today.<br/>
      Analysts say institutional demand remains strong.
      <a href="https://cointelegraph.com/news/example">Read more</a>
    </div>
    <a class="tgme_widget_message_date" href="https://t.me/cointelegraph/12345">
      <time datetime="2026-07-12T08:30:00+00:00">08:30</time>
    </a>
    <span class="tgme_widget_message_views">6.25K</span>
  </div>
  <div class="tgme_widget_message text_not_supported_wrap js-widget_message" data-post="cointelegraph/12346">
    <div class="tgme_widget_message_text js-message_text" dir="auto">
      Ethereum treasury firm announces new purchase after market close.
    </div>
    <a class="tgme_widget_message_date" href="https://t.me/cointelegraph/12346">
      <time datetime="2026-07-12T09:00:00+00:00">09:00</time>
    </a>
    <span class="tgme_widget_message_views">812</span>
  </div>
</body></html>
"""


class TelegramPublicTests(unittest.TestCase):
    def test_normalize_channel_accepts_public_forms(self):
        self.assertEqual(normalize_channel('@cointelegraph'), 'cointelegraph')
        self.assertEqual(normalize_channel('https://t.me/s/cointelegraph'), 'cointelegraph')
        self.assertEqual(normalize_channel('https://t.me/cointelegraph'), 'cointelegraph')
        self.assertEqual(normalize_channel('https://t.me/gram'), 'gram')

    def test_normalize_channel_rejects_private_invites(self):
        with self.assertRaises(ValueError):
            normalize_channel('https://t.me/+privateInvite')

    def test_parse_public_html_returns_rss_shaped_articles(self):
        articles = parse_telegram_public_html(SAMPLE_HTML, 'cointelegraph', 'Cointelegraph Telegram')

        self.assertEqual(len(articles), 2)
        self.assertEqual(articles[0]['source'], 'Cointelegraph Telegram')
        self.assertEqual(articles[0]['sourceType'], 'telegram')
        self.assertEqual(articles[0]['messageId'], '12345')
        self.assertEqual(articles[0]['link'], 'https://t.me/cointelegraph/12345')
        self.assertEqual(articles[0]['pubDate'], '2026-07-12T08:30:00Z')
        self.assertEqual(articles[0]['viewsLabel'], '6.25K')
        self.assertEqual(articles[0]['views'], 6250)
        self.assertIn('Bitcoin ETFs saw fresh inflows today.', articles[0]['title'])
        self.assertIn('institutional demand', articles[0]['desc'])

    def test_filter_posts_by_hours_keeps_recent_posts(self):
        now = datetime.now(timezone.utc)
        articles = [
            {'title': 'fresh', 'pubDate': now.isoformat().replace('+00:00', 'Z')},
            {'title': 'undated', 'pubDate': ''},
            {'title': 'old', 'pubDate': '2020-01-01T00:00:00Z'},
        ]

        filtered = filter_posts_by_hours(articles, 24)
        self.assertEqual([item['title'] for item in filtered], ['fresh', 'undated'])

    def test_parse_view_count(self):
        self.assertEqual(parse_view_count('812'), 812)
        self.assertEqual(parse_view_count('6.25K'), 6250)
        self.assertEqual(parse_view_count('1.2M'), 1200000)
        self.assertIsNone(parse_view_count(''))

    def test_strip_leading_editorial_label(self):
        self.assertEqual(
            strip_leading_editorial_label('🇸🇬 SAFE: Coinbase helped Singapore police prevent over $4.2M in crypto scam losses.'),
            'Coinbase helped Singapore police prevent over $4.2M in crypto scam losses.',
        )
        self.assertEqual(
            strip_leading_editorial_label("🇺🇸 BIG: Custodia Bank has asked the U.S. Supreme Court to review the Fed's denial."),
            "Custodia Bank has asked the U.S. Supreme Court to review the Fed's denial.",
        )
        self.assertEqual(
            strip_leading_editorial_label('Bitcoin ETFs saw fresh inflows today.'),
            'Bitcoin ETFs saw fresh inflows today.',
        )

    def test_rank_by_keyword_match(self):
        class FakeEmbedder:
            def embed(self, texts):
                mapping = {
                    'bitcoin, etf': [1, 0],
                    'Bitcoin ETF inflows rise': [1, 0],
                    'Stablecoin regulation update': [0, 1],
                }
                return [mapping.get(t, [0, 0]) for t in texts]

        articles = [
            {'title': 'Stablecoin regulation update', 'desc': '', 'views': 10000},
            {'title': 'Bitcoin ETF inflows rise', 'desc': '', 'views': 100},
        ]

        ranked = rank_by_keyword_match(articles, ['bitcoin', 'etf'], embedder=FakeEmbedder())
        self.assertEqual(ranked[0]['title'], 'Bitcoin ETF inflows rise')
        self.assertGreater(ranked[0]['keywordScore'], ranked[1]['keywordScore'])

    def test_rank_by_keyword_match_accepts_embedder_stats_tuple(self):
        class FakeEmbedder:
            def embed(self, texts):
                mapping = {
                    'bitcoin, etf': [1, 0],
                    'Bitcoin ETF inflows rise': [1, 0],
                    'Stablecoin regulation update': [0, 1],
                }
                return [mapping.get(t, [0, 0]) for t in texts], 1, 0

        articles = [
            {'title': 'Stablecoin regulation update', 'desc': '', 'views': 10000},
            {'title': 'Bitcoin ETF inflows rise', 'desc': '', 'views': 100},
        ]

        ranked = rank_by_keyword_match(articles, ['bitcoin', 'etf'], embedder=FakeEmbedder())
        self.assertEqual(ranked[0]['title'], 'Bitcoin ETF inflows rise')

    def test_rank_telegram_posts_rejects_keyword_mode_with_less_than_two_keywords(self):
        with self.assertRaises(ValueError):
            rank_telegram_posts({'sortMode': 'keywords', 'topics': 'bitcoin'})

    def test_rank_telegram_posts_latest_sorts_by_publish_date(self):
        fake_posts = {
            'articles': [
                {'title': 'older', 'pubDate': '2026-07-12T08:00:00Z', 'views': 9000},
                {'title': 'newer', 'pubDate': '2026-07-12T12:00:00Z', 'views': 100},
            ],
            'errors': {},
        }
        with patch('telegram_public.fetch_many_telegram_public_posts', return_value=fake_posts):
            ranked = rank_telegram_posts({'sortMode': 'latest', 'topN': 2})

        self.assertEqual(ranked['sortMode'], 'latest')
        self.assertEqual([a['title'] for a in ranked['articles']], ['newer', 'older'])

    def test_rank_telegram_posts_views_per_source_uses_rounds(self):
        fake_posts = {
            'articles': [
                {'title': 'A first', 'channel': 'a', 'views': 1000, 'pubDate': '2026-07-12T10:00:00Z'},
                {'title': 'A second', 'channel': 'a', 'views': 900, 'pubDate': '2026-07-12T09:00:00Z'},
                {'title': 'B first', 'channel': 'b', 'views': 800, 'pubDate': '2026-07-12T08:00:00Z'},
                {'title': 'B second', 'channel': 'b', 'views': 700, 'pubDate': '2026-07-12T07:00:00Z'},
                {'title': 'C first', 'channel': 'c', 'views': 600, 'pubDate': '2026-07-12T06:00:00Z'},
            ],
            'errors': {},
        }
        with patch('telegram_public.fetch_many_telegram_public_posts', return_value=fake_posts):
            ranked = rank_telegram_posts({'sortMode': 'views_per_source', 'topN': 5})

        self.assertEqual(ranked['sortMode'], 'views_per_source')
        self.assertEqual([a['title'] for a in ranked['articles']], ['A first', 'B first', 'C first', 'A second', 'B second'])


if __name__ == '__main__':
    unittest.main()
