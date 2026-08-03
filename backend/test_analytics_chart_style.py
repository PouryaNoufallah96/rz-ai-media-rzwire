import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import database
from analytics_chart_style import DEFAULT_CHART_STYLE, normalize_chart_style


CUSTOM_STYLE = {
    'version': 1,
    'presetId': 'custom',
    'backgroundColor': '#101820',
    'seriesColors': {'rz:mgc': '#F0C419', 'binance:BTC': '#56B4E9'},
    'legend': {'position': 'overlay-bottom-right', 'format': 'symbol'},
    'lineWidth': 6,
    'markers': 'all',
    'gridStrength': 'standard',
}


class AnalyticsChartStyleTests(unittest.TestCase):
    def test_default_and_custom_styles_have_stable_normalized_shapes(self):
        self.assertEqual(normalize_chart_style(), DEFAULT_CHART_STYLE)
        normalized = normalize_chart_style(CUSTOM_STYLE)
        self.assertEqual(normalized['backgroundColor'], '#101820')
        self.assertEqual(normalized['legend']['position'], 'overlay-bottom-right')
        self.assertEqual(normalized['lineWidth'], 6)
        self.assertEqual(list(normalized['seriesColors']), ['binance:BTC', 'rz:mgc'])

    def test_malformed_or_unsupported_values_are_rejected(self):
        cases = [
            {'version': 2},
            {'backgroundColor': 'black'},
            {'seriesColors': {'bad asset id': '#FFFFFF'}},
            {'legend': {'position': 'floating'}},
            {'lineWidth': 5},
            {'markers': 'sometimes'},
            {'gridStrength': 'heavy'},
        ]
        for value in cases:
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize_chart_style(value)

    def test_saved_defaults_are_isolated_by_user_and_brand_and_replace_cleanly(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(database, 'DB_PATH', Path(folder) / 'app.db'):
            database.init_db()
            first = normalize_chart_style(CUSTOM_STYLE)
            second = normalize_chart_style({**CUSTOM_STYLE, 'backgroundColor': '#FFFFFF'})
            database.save_analytics_chart_default(7, 'mgc', first)
            database.save_analytics_chart_default(8, 'mgc', second)
            database.save_analytics_chart_default(7, 'oasis', second)

            self.assertEqual(database.get_analytics_chart_default(7, 'mgc')['style'], first)
            self.assertEqual(database.get_analytics_chart_default(8, 'mgc')['style'], second)
            self.assertEqual(database.get_analytics_chart_default(7, 'oasis')['style'], second)

            replacement = normalize_chart_style({**CUSTOM_STYLE, 'lineWidth': 2})
            database.save_analytics_chart_default(7, 'mgc', replacement)
            self.assertEqual(database.get_analytics_chart_default(7, 'mgc')['style'], replacement)


if __name__ == '__main__':
    unittest.main()
