import unittest

from analytics_image_pipeline import (
    ANALYTICS_TEMPLATE_FAMILIES,
    assemble_analytics_prompt,
    fallback_analytics_brief,
    resolve_analytics_template,
    validate_analytics_brief,
)


THEME_OWNER = {
    'id': 'mgc',
    'name': 'MGC Coin',
    'footer': 'metagamescoin.io',
    'theme': {'background': '#050505', 'accent': '#f1c40f'},
    'motifs': ['signal yellow', 'restrained gold'],
    'imagePrompt': 'Premium black and signal-yellow gaming utility editorial.',
}
SERIES = [
    {'tokenId': 'mgc', 'symbol': 'MGC', 'name': 'MGC Coin', 'role': 'primary',
     'startPrice': 2.4, 'endPrice': 2.8, 'changePercent': 16.67,
     'coverageStart': '2026-07-01', 'coverageEnd': '2026-08-01'},
    {'symbol': 'BTC', 'name': 'Bitcoin', 'role': 'comparison',
     'startPrice': 61560, 'endPrice': 63081.9, 'changePercent': 2.47,
     'coverageStart': '2026-07-01', 'coverageEnd': '2026-08-01'},
]


class AnalyticsImagePipelineTests(unittest.TestCase):
    def test_all_eighteen_registered_variants_resolve(self):
        variants = 0
        for category_id, category in ANALYTICS_TEMPLATE_FAMILIES.items():
            for variant_id in category['variants']:
                resolved = resolve_analytics_template(category_id, variant_id)
                self.assertEqual(resolved['variantId'], variant_id)
                variants += 1
        self.assertEqual(variants, 18)

    def test_variant_must_belong_to_category(self):
        with self.assertRaisesRegex(ValueError, 'does not belong'):
            resolve_analytics_template('phone', 'laptop-cinematic')

    def test_invalid_brief_falls_back_to_binding_sample(self):
        template = resolve_analytics_template('phone', 'phone-centered')
        brief = validate_analytics_brief({'family': 'laptop'}, template, THEME_OWNER, SERIES)
        self.assertEqual(brief['sample_fidelity'], 'binding')
        self.assertEqual(brief['device_strategy'], 'premium phone frame')

    def test_prompt_protects_device_chart_and_brand_facts(self):
        template = resolve_analytics_template('phone', 'phone-centered')
        brief = fallback_analytics_brief(template, THEME_OWNER, SERIES)
        prompt = assemble_analytics_prompt(
            brief, template, THEME_OWNER, {}, {'title': 'MGC vs BTC'},
            'Thirty-day verified comparison.', {'width': 1080, 'height': 1350}, SERIES,
        )
        self.assertIn('REFERENCE 1', prompt)
        self.assertIn('REFERENCE 2', prompt)
        self.assertIn('REFERENCE 3', prompt)
        self.assertIn('inside the device screen', prompt)
        self.assertIn('metagamescoin.io', prompt)
        self.assertIn('phone-centered', prompt)
        self.assertIn('61560', prompt)


if __name__ == '__main__':
    unittest.main()
