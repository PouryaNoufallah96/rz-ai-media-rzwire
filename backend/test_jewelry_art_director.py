import json
import sys
import types
import unittest
from pathlib import Path

from brand_profiles import BRAND_IMAGE_PROFILES

# Exercise the deterministic Art Director profile and compiler without making
# OpenRouter part of the test dependency surface.
if 'llm' not in sys.modules:
    llm_stub = types.ModuleType('llm')
    llm_stub.openrouter_chat = lambda *args, **kwargs: {}
    sys.modules['llm'] = llm_stub

from image_pipeline import (
    _build_art_director_system_prompt,
    assemble_prompt,
    validate_brief,
)


class JewelryArtDirectorTests(unittest.TestCase):
    def setUp(self):
        self.profile = BRAND_IMAGE_PROFILES['Jewelry Coin']

    def test_profile_uses_reference_extracted_bright_crystal_palette(self):
        serialized = json.dumps(self.profile).lower()
        self.assertEqual(self.profile['brand_name'], 'Jewelry Coin')
        for color in (
            '#fafaff', '#ececfe', '#d2c0fd', '#eec7fc', '#9979ff',
            '#552eeb', '#1a094f', '#c3cee4', '#c36ed6',
        ):
            self.assertIn(color, serialized)
        self.assertNotIn('cr_signal', serialized)
        self.assertNotIn('luminous cyan', serialized)
        self.assertNotIn('midnight indigo (#17133d)', serialized)

    def test_reference_led_jewelry_families_replace_generic_profile(self):
        self.assertEqual(set(self.profile['families']), {
            'hero_object',
            'lockup',
            'concept_photo',
            'flat_explainer',
            'stat_card',
            'big_number',
            'type_led',
            'duotone',
            'art_drop',
        })
        self.assertEqual(self.profile['families']['hero_object']['name'], 'PRECIOUS OBJECT HERO')
        self.assertEqual(self.profile['families']['lockup']['name'], 'DIGITAL / PHYSICAL PAIR')
        self.assertEqual(self.profile['families']['concept_photo']['name'], 'CREATOR LIFESTYLE CAMPAIGN')
        self.assertEqual(self.profile['families']['art_drop']['name'], 'CRYSTAL ART DROP')

    def test_owner_approved_reference_assets_are_registered(self):
        assets = self.profile['approved_reference_assets']
        self.assertEqual(len(assets), 10)
        self.assertEqual(
            assets['01 precious object / hero_object'],
            'brand_references/jewelry/approved/01-precious-object-hero.png',
        )
        self.assertEqual(
            assets['10 maker campaign / concept_photo'],
            'brand_references/jewelry/approved/10-creativity-campaign.png',
        )
        for path in assets.values():
            self.assertTrue((Path(__file__).parent / path).is_file(), path)

    def test_every_family_has_valid_default_axes(self):
        stage_axis, composition_axis, energy_axis, accent_axis = self.profile['core_axes']
        axes = self.profile['axes']
        for family_name, family in self.profile['families'].items():
            defaults = family['default_axes']
            with self.subTest(family=family_name):
                self.assertIn(defaults[stage_axis], axes[stage_axis])
                self.assertIn(defaults[composition_axis], axes[composition_axis])
                self.assertIn(defaults[energy_axis], axes[energy_axis])
                self.assertIn(defaults[accent_axis], axes[accent_axis])
                self.assertGreaterEqual(family['data_budget'], 0)

    def test_art_director_prompt_contains_jewelry_contract_and_future_rules(self):
        prompt = _build_art_director_system_prompt(self.profile, [])
        self.assertIn('Art Director for Jewelry Coin', prompt)
        self.assertIn('pearl white (#FAFAFF)', prompt)
        self.assertIn('PRECIOUS OBJECT HERO', prompt)
        self.assertIn('The workspace label is Jewelry Coin', prompt)
        self.assertIn('must appear as planned, intended, proposed, conceptual, or incomplete', prompt)
        self.assertIn('Never use remembered market data', prompt)

    def test_fixed_supply_poster_accepts_only_source_numbers(self):
        article = {
            'title': 'Jewelry has a fixed total supply of 100,000,000 tokens',
            'desc': 'The reviewed whitepaper lists a total supply of 100,000,000 and 9 decimals.',
        }
        base = {
            'family': 'big_number',
            'headline': 'Fixed total supply',
            'data_elements': [{'value': '100,000,000', 'label': 'JEWELRY'}],
            'stage': 'lavender_gradient',
            'composition': 'number_showcase',
            'energy': 'milestone',
            'accent': 'crystal_violet',
            'art_style': '',
            'subject_scene': (
                'The verified supply figure appears as one large crystal-like typographic form above '
                'a frosted plinth on a pearl-to-lavender field.'
            ),
        }
        valid = validate_brief(base, article, self.profile)
        self.assertEqual(valid['family'], 'big_number')
        self.assertEqual(valid['data_elements'][0]['value'], '100,000,000')

        invalid = validate_brief(
            {**base, 'data_elements': [{'value': '250,000,000', 'label': 'JEWELRY'}]},
            article,
            self.profile,
        )
        self.assertEqual(invalid['family'], 'hero_object')

    def test_live_marketplace_and_guaranteed_production_claims_are_rejected(self):
        article = {
            'title': 'Jewelry proposes a creator ecosystem',
            'desc': 'The marketplace and physical-production path are described as planned features.',
        }
        unsafe = {
            'family': 'lockup',
            'headline': 'Shop The Live Marketplace Today',
            'data_elements': [],
            'stage': 'lavender_gradient',
            'composition': 'split_transformation',
            'energy': 'creator_confidence',
            'accent': 'glass_violet',
            'art_style': '',
            'subject_scene': (
                'A live marketplace guarantees instant physical jewelry through an official jewelry partner.'
            ),
        }
        brief = validate_brief(unsafe, article, self.profile)
        self.assertEqual(brief['family'], 'hero_object')
        self.assertEqual(brief['headline'], 'Jewelry proposes a creator ecosystem')

        prompt = assemble_prompt(brief, self.profile)
        self.assertIn('pearl white (#FAFAFF)', prompt)
        self.assertIn('Headline text: "Jewelry proposes a creator ecosystem"', prompt)
        self.assertIn('No other text anywhere in the image', prompt)


if __name__ == '__main__':
    unittest.main()
