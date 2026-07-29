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


if __name__ == '__main__':
    unittest.main()
