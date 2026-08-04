import unittest
from unittest.mock import patch

from analytics_image_pipeline import (
    ANALYTICS_TEMPLATE_FAMILIES,
    assemble_analytics_prompt,
    call_analytics_art_director,
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
    'backgroundScenes': [
        'A monumental black gaming city with a controlled signal-yellow sunrise, cinematic architecture, restrained haze, and generous editorial negative space.',
        'An obsidian digital arena with a restrained gold energy core, deep graphite atmosphere, cinematic side light, and calm editorial negative space.',
        'A black orbital landscape with precise gold signal paths, a luminous horizon, premium scale, quiet typography space, and no data graphics.',
    ],
}
SERIES = [
    {'id': 'rz:mgc', 'tokenId': 'mgc', 'symbol': 'MGC', 'name': 'MGC Coin', 'role': 'primary', 'color': '#F0C419',
     'startPrice': 2.4, 'endPrice': 2.8, 'changePercent': 16.67,
     'coverageStart': '2026-07-01', 'coverageEnd': '2026-08-01'},
    {'id': 'binance:BTC', 'symbol': 'BTC', 'name': 'Bitcoin', 'role': 'comparison', 'color': '#0072B2',
     'startPrice': 61560, 'endPrice': 63081.9, 'changePercent': 2.47,
     'coverageStart': '2026-07-01', 'coverageEnd': '2026-08-01'},
]
CHART_STYLE = {
    'version': 1, 'presetId': 'custom', 'backgroundColor': '#101820',
    'seriesColors': {'rz:mgc': '#F0C419', 'binance:BTC': '#0072B2'},
    'legend': {'position': 'overlay-top-right', 'format': 'symbol-change'},
    'lineWidth': 6, 'markers': 'all', 'gridStrength': 'standard',
}


class AnalyticsImagePipelineTests(unittest.TestCase):
    def test_all_eighteen_registered_variants_resolve(self):
        required_contract_fields = {
            'summary', 'skeleton', 'chart', 'typography',
            'brandTranslation', 'finish', 'forbidden',
        }
        variants = 0
        for category_id, category in ANALYTICS_TEMPLATE_FAMILIES.items():
            for variant_id in category['variants']:
                resolved = resolve_analytics_template(category_id, variant_id)
                self.assertEqual(resolved['variantId'], variant_id)
                self.assertEqual(set(resolved['contract']), required_contract_fields)
                for value in resolved['contract'].values():
                    self.assertGreater(len(value), 40)
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

    def test_prompt_is_a_complete_two_reference_card_specification(self):
        template = resolve_analytics_template('phone', 'phone-centered')
        brief = fallback_analytics_brief(template, THEME_OWNER, SERIES)
        prompt = assemble_analytics_prompt(
            brief, template, THEME_OWNER, {}, {'title': 'MGC vs BTC'},
            'Thirty-day verified comparison.', {'width': 1080, 'height': 1350}, SERIES,
            chart_style=CHART_STYLE,
        )
        self.assertIn('exactly TWO ordered references', prompt)
        self.assertIn('REFERENCE 1', prompt)
        self.assertIn('REFERENCE 2', prompt)
        self.assertNotIn('REFERENCE 3', prompt)
        self.assertIn('inside the device screen', prompt)
        self.assertIn('metagamescoin.io', prompt)
        self.assertIn('phone-centered', prompt)
        self.assertIn('61560', prompt)
        self.assertIn('FULL IMMUTABLE FAMILY CONTRACT', prompt)
        self.assertIn('FULL ART DIRECTOR PRODUCTION BRIEF', prompt)
        self.assertIn('CANVAS AND MODULE MAP', prompt)
        self.assertIn('DEVICE OR CARD CONSTRUCTION', prompt)
        self.assertIn('TYPOGRAPHY SYSTEM', prompt)
        self.assertIn('CHART APERTURE AND INTEGRATION', prompt)
        self.assertIn('LOGO AND FOOTER SYSTEM', prompt)
        self.assertIn('FORBIDDEN CHANGES', prompt)
        self.assertIn('EXECUTION ORDER', prompt)
        self.assertIn('first reproduce Reference 1 composition', prompt)
        self.assertIn('APPROVED CHART PRESENTATION', prompt)
        self.assertIn('overlay-top-right', prompt)
        self.assertIn('#0072B2', prompt)
        self.assertIn('"lineWidth":6', prompt)
        self.assertIn('CHART SCALE LIMIT', prompt)
        self.assertIn('SELECTED DRAMATIC OWNER BACKGROUND', prompt)
        self.assertIn(THEME_OWNER['backgroundScenes'][0], prompt)
        self.assertIn('show each exactly once', prompt)
        self.assertIn('protected footer rail', prompt)
        self.assertIn('left logo slot empty', prompt)
        self.assertIn('preserving its aspect ratio', prompt)

    @patch('analytics_image_pipeline.openrouter_chat')
    def test_art_director_receives_selected_sample_as_visual_reference(self, chat):
        chat.return_value = fallback_analytics_brief(
            resolve_analytics_template('phone', 'phone-centered'), THEME_OWNER, SERIES,
        )
        sample = 'data:image/png;base64,approved-template'
        call_analytics_art_director(
            {'title': 'MGC vs BTC'}, 'Thirty-day verified comparison.', THEME_OWNER,
            {'frozen_style': {'visual_world': 'premium'}},
            resolve_analytics_template('phone', 'phone-centered'),
            {'width': 1080, 'height': 1920}, SERIES,
            sample_reference=sample, chart_style=CHART_STYLE,
        )
        messages = chat.call_args.args[1]
        self.assertIsInstance(messages[1]['content'], list)
        self.assertEqual(messages[1]['content'][1]['type'], 'image_url')
        self.assertEqual(messages[1]['content'][1]['image_url']['url'], sample)
        self.assertIn('BINDING', messages[0]['content'])
        self.assertIn('VARIANT CONTRACT', messages[0]['content'])
        self.assertIn('chart/device aperture', messages[0]['content'])
        self.assertIn('NO captured composition reference', messages[0]['content'])
        self.assertIn('complete construction specification', messages[0]['content'])
        self.assertIn('APPROVED OWNER BACKGROUND SCENES', messages[0]['content'])
        self.assertIn('IMMUTABLE CHART SCALE RULE', messages[0]['content'])
        self.assertIn('do not recreate either outside it', messages[0]['content'])
        self.assertIn('Approved chart presentation', messages[1]['content'][0]['text'])
        self.assertIn('overlay-top-right', messages[1]['content'][0]['text'])

    def test_fallback_is_a_complete_production_brief(self):
        template = resolve_analytics_template('laptop', 'laptop-cinematic')
        brief = fallback_analytics_brief(template, THEME_OWNER, SERIES)
        for field in (
            'reference_analysis', 'composition_map', 'chart_integration',
            'typography_system', 'data_hierarchy', 'brand_translation',
            'materials_and_finish', 'logo_footer_system', 'quality_control',
            'forbidden_changes',
        ):
            self.assertTrue(brief[field])
        self.assertEqual(brief['composition_map'], template['contract']['skeleton'])
        self.assertEqual(brief['chart_integration'], template['contract']['chart'])

    def test_growth_card_uses_smaller_chart_and_owner_scene(self):
        template = resolve_analytics_template('growth', 'growth-card')
        brief = fallback_analytics_brief(template, THEME_OWNER, SERIES)
        self.assertIn('30-38%', brief['chart_scale'])
        self.assertEqual(brief['background_scene'], THEME_OWNER['backgroundScenes'][0])
        self.assertIn('no more than three lines', template['contract']['typography'])
        self.assertIn('no chart taller than 38%', template['contract']['forbidden'])

    def test_unapproved_art_director_background_is_replaced(self):
        template = resolve_analytics_template('growth', 'growth-card')
        raw = fallback_analytics_brief(template, THEME_OWNER, SERIES)
        raw['background_scene'] = 'Generic neon crypto wallpaper.'
        raw['chart_scale'] = 'Fill the entire canvas.'
        brief = validate_analytics_brief(raw, template, THEME_OWNER, SERIES)
        self.assertEqual(brief['background_scene'], THEME_OWNER['backgroundScenes'][0])
        self.assertIn('30-38%', brief['chart_scale'])

    def test_every_family_reserves_a_collision_free_logo_footer(self):
        for category_id, category in ANALYTICS_TEMPLATE_FAMILIES.items():
            variant_id = next(iter(category['variants']))
            template = resolve_analytics_template(category_id, variant_id)
            brief = fallback_analytics_brief(template, THEME_OWNER, SERIES)
            rule = brief['logo_footer_system']
            self.assertIn('protected footer rail', rule)
            self.assertIn('leftmost 16%', rule)
            self.assertIn('no card, result strip, text', rule)
            self.assertIn('preserving its aspect ratio', rule)
            self.assertIn(THEME_OWNER['footer'], rule)

    def test_art_director_cannot_override_protected_logo_slot(self):
        template = resolve_analytics_template('laptop', 'laptop-cinematic')
        raw = fallback_analytics_brief(template, THEME_OWNER, SERIES)
        raw['logo_footer_system'] = 'Put a giant logo over the result cards.'
        brief = validate_analytics_brief(raw, template, THEME_OWNER, SERIES)
        self.assertNotIn('giant logo', brief['logo_footer_system'])
        self.assertIn('result strip must end above it', brief['logo_footer_system'])


if __name__ == '__main__':
    unittest.main()
