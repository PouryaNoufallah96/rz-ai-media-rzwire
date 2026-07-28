import json
import sys
import types
import unittest

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


class RankingArtDirectorTests(unittest.TestCase):
    def setUp(self):
        self.profile = BRAND_IMAGE_PROFILES['Ranking Platform']

    def test_profile_is_reference_led_and_not_legacy_clone(self):
        serialized = json.dumps(self.profile).lower()
        self.assertEqual(self.profile['brand_name'], 'Ranking Platform')
        self.assertIn('#20113d', serialized)
        self.assertIn('#ff4f91', serialized)
        self.assertIn('#55e6a3', serialized)
        self.assertIn('#ff8a48', serialized)
        self.assertNotIn('cr_signal', serialized)
        self.assertNotIn('gradient_sweep', serialized)

    def test_reference_derived_campaign_families_are_available(self):
        expected = {
            'player_spotlight',
            'platform_in_action',
            'profile_hero',
            'achievement_moment',
            'versus_match',
            'game_culture',
            'editorial_window',
            'fact_poster',
            'feature_explainer',
            'role_wheel',
            'ranking_ladder',
            'ranking_calendar',
            'tournament_deck',
            'game_grid',
            'venue_story',
            'sticker_still_life',
            'announcement',
        }
        self.assertEqual(set(self.profile['families']), expected)

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

    def test_art_director_prompt_contains_ranking_visual_contract(self):
        prompt = _build_art_director_system_prompt(self.profile, [])
        self.assertIn('Art Director for Ranking Platform', prompt)
        self.assertIn('hot pink (#FF4F91)', prompt)
        self.assertIn('TOURNAMENT CARD DECK', prompt)
        self.assertIn('Ranking Platform is a platform, never a token', prompt)
        self.assertIn('linked-node', prompt)

    def test_verified_fact_poster_accepts_only_source_numbers(self):
        article = {
            'title': 'The 1972 arcade milestone that changed gaming',
            'desc': 'The first major commercial chapter began in 1972.',
        }
        base = {
            'family': 'fact_poster',
            'headline': 'The Match That Started An Era',
            'data_elements': [{'value': '1972', 'label': 'ARCADE MILESTONE'}],
            'stage': 'documentary_photo',
            'composition': 'fact_stack',
            'energy': 'editorial_energy',
            'accent': 'mint_field',
            'subject_scene': (
                'A moody archive-style row of early arcade cabinets fills the frame under a subtle '
                'aubergine wash with a quiet upper-left region.'
            ),
        }
        valid = validate_brief(base, article, self.profile)
        self.assertEqual(valid['family'], 'fact_poster')
        self.assertEqual(valid['data_elements'][0]['value'], '1972')

        invalid = validate_brief(
            {**base, 'data_elements': [{'value': '$25M', 'label': 'PRIZE'}]},
            article,
            self.profile,
        )
        self.assertEqual(invalid['family'], 'ranking_ladder')

    def test_financial_scene_is_rejected_and_prompt_uses_brand_system(self):
        article = {
            'title': 'Ranking makes competitive play visible',
            'desc': 'Profiles record game-specific progress and match history.',
        }
        unsafe = {
            'family': 'profile_hero',
            'headline': 'Build Your Competitive Identity',
            'data_elements': [],
            'stage': 'bright_graphic',
            'composition': 'centered_card',
            'energy': 'confident_product',
            'accent': 'pink_mint',
            'subject_scene': 'A player card floats above an ethereum diamond and line chart.',
        }
        brief = validate_brief(unsafe, article, self.profile)
        self.assertEqual(brief['family'], 'ranking_ladder')

        prompt = assemble_prompt(brief, self.profile)
        self.assertIn('deep aubergine (#20113D)', prompt)
        self.assertIn('Headline text: "RANKING MAKES COMPETITIVE PLAY VISIBLE"', prompt)
        self.assertIn('No other text anywhere in the image', prompt)


if __name__ == '__main__':
    unittest.main()
