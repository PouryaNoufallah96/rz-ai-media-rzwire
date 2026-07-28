import json
import sys
import types
import unittest
from pathlib import Path

from brand_profiles import BRAND_IMAGE_PROFILES

# These tests exercise the deterministic profile and prompt compiler only. Keep
# the OpenRouter transport out of the test dependency surface.
if 'llm' not in sys.modules:
    llm_stub = types.ModuleType('llm')
    llm_stub.openrouter_chat = lambda *args, **kwargs: {}
    sys.modules['llm'] = llm_stub

from image_pipeline import (
    _build_art_director_system_prompt,
    assemble_prompt,
    validate_brief,
)


class OasisArtDirectorTests(unittest.TestCase):
    def setUp(self):
        self.profile = BRAND_IMAGE_PROFILES['Oasis Coin']

    def test_profile_uses_extracted_monochrome_palette(self):
        serialized = json.dumps(self.profile).lower()
        self.assertEqual(self.profile['brand_name'], 'Oasis Coin')
        for color in ('#000000', '#0d0e18', '#191a25', '#222531', '#4e4f5b', '#a3a5a7', '#f4f3f0'):
            self.assertIn(color, serialized)
        self.assertIn('#20c98b', serialized)
        self.assertNotIn('cr_signal', serialized)
        self.assertNotIn('luminous cyan', serialized)

    def test_editorial_families_are_reauthored_for_oasis(self):
        self.assertEqual(set(self.profile['families']), {
            'duotone',
            'big_number',
            'hero_object',
            'concept_photo',
            'flat_explainer',
            'type_led',
            'art_drop',
            'stat_card',
            'roadmap_card',
            'lockup',
        })
        self.assertEqual(self.profile['families']['duotone']['name'], 'MONOCHROME ECLIPSE EDITORIAL')
        self.assertEqual(self.profile['families']['type_led']['name'], 'BLACK-FIELD STATEMENT')
        self.assertEqual(self.profile['families']['stat_card']['name'], 'VERIFIED DATA CARD')
        self.assertEqual(self.profile['families']['roadmap_card']['name'], 'PHASED ROADMAP CARDS')

    def test_owner_approved_reference_assets_are_registered(self):
        assets = self.profile['approved_reference_assets']
        self.assertEqual(len(assets), 10)
        backend_dir = Path(__file__).resolve().parent
        for direction, relative_path in assets.items():
            with self.subTest(direction=direction):
                self.assertTrue((backend_dir / relative_path).is_file())

    def test_roadmap_cards_do_not_require_invented_numeric_data(self):
        self.assertNotIn('roadmap_card', self.profile['families_requiring_data'])
        article = {
            'title': 'Oasis development continues in phases',
            'desc': 'The published stages are Foundation, Infrastructure, and Future Worlds.',
        }
        brief = validate_brief({
            'family': 'roadmap_card',
            'headline': 'A system built in stages',
            'data_elements': [
                {'value': 'FOUNDATION', 'label': ''},
                {'value': 'INFRASTRUCTURE', 'label': ''},
                {'value': 'FUTURE WORLDS', 'label': ''},
            ],
            'stage': 'graphite_data',
            'composition': 'card_grid',
            'energy': 'architectural_calm',
            'accent': 'lunar_silver',
            'art_style': '',
            'subject_scene': 'Three staggered obsidian phase cards connected by one thin silver path.',
        }, article, self.profile)
        self.assertEqual(brief['family'], 'roadmap_card')
        self.assertEqual(len(brief['data_elements']), 3)

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

    def test_art_director_prompt_contains_honest_future_state_rules(self):
        prompt = _build_art_director_system_prompt(self.profile, [])
        self.assertIn('Art Director for Oasis Coin', prompt)
        self.assertIn('absolute black (#000000)', prompt)
        self.assertIn('BLACK-FIELD STATEMENT', prompt)
        self.assertIn('OASIS is the token; RZOASIS is the ecosystem or galaxy', prompt)
        self.assertIn('future modules remain incomplete', prompt)
        self.assertIn('Never use remembered live-market data', prompt)

    def test_verified_market_poster_accepts_only_source_numbers(self):
        article = {
            'title': 'OASIS closes at $0.9339 after a 9.11% monthly increase',
            'desc': 'The reported one-month move was 9.11%, with the displayed price at $0.9339.',
        }
        base = {
            'family': 'big_number',
            'headline': 'One month of measured movement',
            'data_elements': [{'value': '$0.9339', 'label': 'OASIS'}],
            'stage': 'graphite_data',
            'composition': 'number_orbit',
            'energy': 'measured_momentum',
            'accent': 'emerald_data',
            'art_style': '',
            'subject_scene': (
                'One large white value dominates a graphite field beneath a thin silver eclipse arc '
                'while a compact dark module carries a restrained emerald historical trace.'
            ),
        }
        valid = validate_brief(base, article, self.profile)
        self.assertEqual(valid['family'], 'big_number')
        self.assertEqual(valid['data_elements'][0]['value'], '$0.9339')

        invalid = validate_brief(
            {**base, 'data_elements': [{'value': '$2.50', 'label': 'TARGET'}]},
            article,
            self.profile,
        )
        self.assertEqual(invalid['family'], 'concept_photo')

    def test_live_metaverse_claim_is_rejected(self):
        article = {
            'title': 'Oasis is building its galaxy in phases',
            'desc': 'The long-term ecosystem remains under development.',
        }
        unsafe = {
            'family': 'concept_photo',
            'headline': 'Enter The Finished Galaxy Today',
            'data_elements': [],
            'stage': 'deep_space',
            'composition': 'horizon_campaign',
            'energy': 'quiet_vision',
            'accent': 'deep_space_blue',
            'art_style': '',
            'subject_scene': 'A finished metaverse welcomes users into a live marketplace of completed worlds.',
        }
        brief = validate_brief(unsafe, article, self.profile)
        self.assertEqual(brief['family'], 'concept_photo')
        self.assertEqual(brief['headline'], 'Oasis is building its galaxy in phases')

        prompt = assemble_prompt(brief, self.profile)
        self.assertIn('absolute black (#000000)', prompt)
        self.assertIn('Headline text: "Oasis is building its galaxy in phases"', prompt)
        self.assertIn('No other text anywhere in the image', prompt)


if __name__ == '__main__':
    unittest.main()
