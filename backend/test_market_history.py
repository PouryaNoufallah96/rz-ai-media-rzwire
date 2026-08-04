import unittest
from unittest.mock import patch

from handlers import market


class _Response:
    def __init__(self, data):
        self._data = data
        self.status_code = 200
        self.headers = {}

    def raise_for_status(self):
        return None

    def json(self):
        return self._data


class MarketHistoryTests(unittest.TestCase):
    def setUp(self):
        market._CACHE.clear()
        market._SERIES_CACHE.clear()
        market._CATALOG_CACHE = None

    @patch('handlers.market.requests.get')
    def test_returns_verified_primary_and_comparison_history(self, get):
        get.side_effect = [
            _Response({'data': {'attributes': {'ohlcv_list': [
                [2, 11, 12, 10, 12, 200],
                [1, 9, 11, 8, 10, 100],
            ]}}}),
            _Response([
                [1000, '20', '22', '19', '21', '50'],
                [2000, '21', '23', '20', '22', '60'],
            ]),
        ]

        result = market.handle_market_history({'token': ['mgc'], 'period': ['30d'], 'compare': ['BTC']})

        self.assertTrue(result['verified'])
        self.assertFalse(result['sample'])
        self.assertEqual(result['primary']['points'][0]['close'], 10)
        self.assertEqual(result['primary']['points'][-1]['close'], 12)
        self.assertAlmostEqual(result['primary']['changePercent'], 20)
        self.assertEqual(result['comparison']['symbol'], 'BTC')
        self.assertEqual(len(result['sources']), 2)

    def test_rejects_unknown_token(self):
        with self.assertRaisesRegex(ValueError, 'token must be'):
            market.handle_market_history({'token': ['unknown']})

    @patch('handlers.market.requests.get')
    def test_long_ranges_use_supported_daily_aggregate(self, get):
        get.return_value = _Response({'data': {'attributes': {'ohlcv_list': [
            [2, 11, 12, 10, 12, 200],
            [1, 9, 11, 8, 10, 100],
        ]}}})

        market._gecko_history(market.TOKEN_CONFIG['mgc'], '90d')
        ninety_day_params = get.call_args.kwargs['params']
        self.assertEqual(ninety_day_params['aggregate'], 1)
        self.assertEqual(ninety_day_params['limit'], 91)

        market._gecko_history(market.TOKEN_CONFIG['mgc'], '1y')
        one_year_params = get.call_args.kwargs['params']
        self.assertEqual(one_year_params['aggregate'], 1)
        self.assertEqual(one_year_params['limit'], 366)

    @patch('handlers.market._binance_history')
    @patch('handlers.market._gecko_history')
    def test_batch_returns_six_ordered_series(self, gecko_history, binance_history):
        def gecko_result(token, _period):
            base = {'MGC': 10, 'OASIS': 20, 'JEWELRY': 30}[token['symbol']]
            return market._series_summary(token['name'], token['symbol'], [
                {'timestamp': 1000, 'close': base},
                {'timestamp': 2000, 'close': base * 1.1},
            ]), {'provider': 'GeckoTerminal', 'url': 'https://example.test/gecko'}

        def binance_result(symbol, _period):
            base = {'BTC': 100, 'ETH': 200, 'XRP': 300}[symbol]
            return market._series_summary(symbol, symbol, [
                {'timestamp': 1000, 'close': base},
                {'timestamp': 2000, 'close': base * 0.9},
            ]), {'provider': 'Binance', 'url': 'https://example.test/binance'}

        gecko_history.side_effect = gecko_result
        binance_history.side_effect = binance_result
        result = market.handle_market_history_batch({
            'primaryTokens': ['mgc', 'oasis', 'jewelry'],
            'comparisonAssets': [
                {'type': 'binance', 'symbol': 'BTC'},
                {'type': 'binance', 'symbol': 'ETH'},
                {'type': 'binance', 'symbol': 'XRP'},
            ],
            'period': '30d',
            'scale': 'relative',
        })

        self.assertTrue(result['verified'])
        self.assertFalse(result['partial'])
        self.assertEqual([item['symbol'] for item in result['series']], [
            'MGC', 'OASIS', 'JEWELRY', 'BTC', 'ETH', 'XRP',
        ])
        self.assertEqual(len(result['sources']), 6)

    @patch('handlers.market._binance_history')
    @patch('handlers.market._gecko_history')
    def test_batch_keeps_successful_series_when_one_provider_fails(self, gecko_history, binance_history):
        gecko_history.return_value = (
            market._series_summary('MGC Coin', 'MGC', [
                {'timestamp': 1000, 'close': 10},
                {'timestamp': 2000, 'close': 12},
            ]),
            {'provider': 'GeckoTerminal', 'url': 'https://example.test/gecko'},
        )
        binance_history.side_effect = RuntimeError('provider unavailable')

        result = market.handle_market_history_batch({
            'primaryTokens': ['mgc'],
            'comparisonAssets': [{'type': 'binance', 'symbol': 'BTC'}],
            'period': '7d',
            'scale': 'absolute',
        })

        self.assertTrue(result['verified'])
        self.assertTrue(result['partial'])
        self.assertEqual(len(result['series']), 1)
        self.assertEqual(result['failures'][0]['symbol'], 'BTC')
        self.assertIn('BTC could not be loaded', result['warnings'][0])

    @patch('handlers.market._binance_history')
    @patch('handlers.market._gecko_history')
    def test_batch_strictly_clips_every_series_to_selected_24_hours(self, gecko_history, binance_history):
        gecko_history.return_value = (
            market._series_summary('Jewelry Coin', 'JEWELRY', [
                {'timestamp': 1_000, 'close': 30},
                {'timestamp': 2_000, 'close': 31},
                {'timestamp': 350_000, 'close': 28},
                {'timestamp': 400_000, 'close': 29},
            ]),
            {'provider': 'GeckoTerminal', 'url': 'https://example.test/gecko'},
        )
        binance_history.return_value = (
            market._series_summary('XRP', 'XRP', [
                {'timestamp': 313_600, 'close': 1.0},
                {'timestamp': 350_000, 'close': 1.1},
                {'timestamp': 400_000, 'close': 1.2},
            ]),
            {'provider': 'Binance', 'url': 'https://example.test/binance'},
        )

        result = market.handle_market_history_batch({
            'primaryTokens': ['jewelry'],
            'comparisonAssets': [{'type': 'binance', 'symbol': 'XRP'}],
            'period': '24h',
            'scale': 'relative',
        })

        self.assertEqual(result['windowStart'], 313_600)
        self.assertEqual(result['windowEnd'], 400_000)
        self.assertEqual([point['timestamp'] for point in result['series'][0]['points']], [350_000, 400_000])
        self.assertEqual(result['series'][0]['startPrice'], 28)
        self.assertEqual(result['series'][0]['endPrice'], 29)
        self.assertTrue(all(
            result['windowStart'] <= point['timestamp'] <= result['windowEnd']
            for series in result['series'] for point in series['points']
        ))

    @patch('handlers.market._binance_history')
    @patch('handlers.market._gecko_history')
    def test_batch_does_not_backfill_old_prices_when_24h_data_is_insufficient(self, gecko_history, binance_history):
        gecko_history.return_value = (
            market._series_summary('Jewelry Coin', 'JEWELRY', [
                {'timestamp': 1_000, 'close': 30},
                {'timestamp': 2_000, 'close': 31},
            ]),
            {'provider': 'GeckoTerminal', 'url': 'https://example.test/gecko'},
        )
        binance_history.return_value = (
            market._series_summary('XRP', 'XRP', [
                {'timestamp': 350_000, 'close': 1.1},
                {'timestamp': 400_000, 'close': 1.2},
            ]),
            {'provider': 'Binance', 'url': 'https://example.test/binance'},
        )

        result = market.handle_market_history_batch({
            'primaryTokens': ['jewelry'],
            'comparisonAssets': [{'type': 'binance', 'symbol': 'XRP'}],
            'period': '24h',
            'scale': 'relative',
        })

        self.assertFalse(result['verified'])
        self.assertEqual([item['symbol'] for item in result['series']], ['XRP'])
        self.assertEqual(result['failures'][0]['symbol'], 'JEWELRY')
        self.assertIn('older candles were not substituted', result['failures'][0]['error'])

    def test_batch_rejects_duplicates_and_selection_limits(self):
        with self.assertRaisesRegex(ValueError, 'only be selected once'):
            market.handle_market_history_batch({
                'primaryTokens': ['mgc', 'mgc'],
                'comparisonAssets': [],
            })
        with self.assertRaisesRegex(ValueError, 'no more than three comparison'):
            market.handle_market_history_batch({
                'primaryTokens': ['mgc'],
                'comparisonAssets': [
                    {'symbol': 'BTC'}, {'symbol': 'ETH'}, {'symbol': 'XRP'}, {'symbol': 'BNB'},
                ],
            })

    @patch('handlers.market._binance_history')
    @patch('handlers.market._gecko_history')
    def test_batch_supports_one_two_three_and_six_series_in_both_scales(self, gecko_history, binance_history):
        def gecko_result(token, _period):
            return market._series_summary(token['name'], token['symbol'], [
                {'timestamp': 1000, 'close': 1}, {'timestamp': 2000, 'close': 2},
            ]), {'provider': 'GeckoTerminal', 'url': 'https://example.test/gecko'}

        def binance_result(symbol, _period):
            return market._series_summary(symbol, symbol, [
                {'timestamp': 1000, 'close': 10}, {'timestamp': 2000, 'close': 11},
            ]), {'provider': 'Binance', 'url': 'https://example.test/binance'}

        gecko_history.side_effect = gecko_result
        binance_history.side_effect = binance_result
        selections = [
            (['mgc'], []),
            (['mgc'], [{'symbol': 'BTC'}]),
            (['mgc', 'oasis'], [{'symbol': 'BTC'}]),
            (['mgc', 'oasis', 'jewelry'], [{'symbol': 'BTC'}, {'symbol': 'ETH'}, {'symbol': 'XRP'}]),
        ]
        for scale in ('relative', 'absolute'):
            for primaries, comparisons in selections:
                with self.subTest(scale=scale, count=len(primaries) + len(comparisons)):
                    market._SERIES_CACHE.clear()
                    result = market.handle_market_history_batch({
                        'primaryTokens': primaries,
                        'comparisonAssets': comparisons,
                        'period': '30d',
                        'scale': scale,
                    })
                    self.assertEqual(result['scale'], scale)
                    self.assertEqual(len(result['series']), len(primaries) + len(comparisons))
                    self.assertTrue(result['verified'])

    @patch('handlers.market.requests.get')
    def test_asset_search_returns_active_binance_usdt_markets(self, get):
        get.return_value = _Response({'symbols': [
            {
                'symbol': 'BTCUSDT', 'baseAsset': 'BTC', 'quoteAsset': 'USDT',
                'status': 'TRADING', 'isSpotTradingAllowed': True,
            },
            {
                'symbol': 'OLDUSDT', 'baseAsset': 'OLD', 'quoteAsset': 'USDT',
                'status': 'BREAK', 'isSpotTradingAllowed': True,
            },
            {
                'symbol': 'ETHBTC', 'baseAsset': 'ETH', 'quoteAsset': 'BTC',
                'status': 'TRADING', 'isSpotTradingAllowed': True,
            },
        ]})

        result = market.handle_market_assets({'q': ['btc']})

        self.assertEqual(len(result['assets']), 1)
        self.assertEqual(result['assets'][0]['symbol'], 'BTC')

    @patch('handlers.market._best_pool')
    @patch('handlers.market._gecko_token_profile')
    def test_resolves_custom_dex_token(self, token_profile, best_pool):
        token_profile.return_value = {
            'name': 'Custom Coin', 'symbol': 'CSTM', 'network': 'bsc',
            'contract': '0x771e1c638a9409bfc93158588f1745f638f4d10b',
        }
        best_pool.return_value = ({'attributes': {
            'name': 'CSTM / USDT',
            'address': '0x1111111111111111111111111111111111111111',
        }}, 'base')

        result = market.handle_resolve_dex_asset({
            'network': 'bsc',
            'contract': '0x771e1c638a9409bfc93158588f1745f638f4d10b',
        })

        self.assertTrue(result['verified'])
        self.assertEqual(result['asset']['symbol'], 'CSTM')
        self.assertEqual(result['asset']['poolName'], 'CSTM / USDT')


if __name__ == '__main__':
    unittest.main()
