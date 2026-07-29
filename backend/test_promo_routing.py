import unittest
from unittest.mock import patch

from _branddoc import _brand_doc
from config import BRAND_HASHTAGS, BRAND_PROMO_PITCH, MEDIA_LIST
from handlers.copy import handle_generate_copy
from handlers.image import handle_promo_ideas


PLATFORMS = ('X', 'Telegram', 'Instagram')


class PromoRoutingTests(unittest.TestCase):
    def test_every_media_has_promotional_brand_context(self):
        self.assertEqual(set(MEDIA_LIST), set(BRAND_PROMO_PITCH))
        self.assertEqual(set(MEDIA_LIST), set(BRAND_HASHTAGS))
        for brand in MEDIA_LIST:
            context = _brand_doc(brand)
            self.assertTrue(context.strip(), brand)
            self.assertGreaterEqual(len(context), len(BRAND_PROMO_PITCH[brand]))

    def test_promo_idea_generation_uses_the_selected_media_bible(self):
        captured = []

        def fake_chat(_model, messages, **_kwargs):
            captured.append(messages[0]['content'])
            return [
                {
                    'title': f'Brand-led promotional idea {index}',
                    'description': 'A credible, mechanism-led explanation of the selected brand.',
                    'angle': f'Angle {index}',
                }
                for index in range(1, 5)
            ]

        with patch('handlers.image.openrouter_chat', side_effect=fake_chat):
            for brand in MEDIA_LIST:
                result = handle_promo_ideas({
                    'brand': brand,
                    'prompt': 'Explain what makes this product useful.',
                    'modelKey': 'gpt',
                    'language': 'en',
                })
                self.assertNotIn('error', result, brand)
                self.assertEqual(len(result['ideas']), 4, brand)
                system_prompt = captured[-1]
                self.assertIn(brand, system_prompt)
                self.assertIn(_brand_doc(brand), system_prompt)

    def test_promo_copy_stays_brand_specific_on_every_platform(self):
        captured = []

        def fake_chat(_model, messages, *_args, **_kwargs):
            system_prompt = messages[0]['content']
            captured.append(system_prompt)
            brand = next(name for name in MEDIA_LIST if f'content for {name}.' in system_prompt)
            if 'promotional Telegram content' in system_prompt:
                copy = (
                    f'{brand} turns a clear product mechanism into practical participation. '
                    'This post explains what the product does today, who it serves, and why its '
                    'design matters without promising returns or overstating future utility. '
                    'Readers get a concise, credible view of the benefit and the next useful step. '
                    'The focus stays on verified product facts and responsible participation.'
                )
            elif 'promotional Instagram content' in system_prompt:
                copy = (
                    f'{brand} is built around a real product idea worth understanding. '
                    'Here is how its mechanism connects people, participation, and useful digital experiences. '
                    'Explore the product story and decide where you fit.'
                )
            else:
                copy = f'{brand} turns a defined product mechanism into useful digital participation. See how it works.'
            return {'copy': copy, 'hashtags': ['#Web3']}

        with patch('handlers.copy.openrouter_chat', side_effect=fake_chat):
            for brand in MEDIA_LIST:
                for platform in PLATFORMS:
                    start = len(captured)
                    result = handle_generate_copy({
                        'article': {
                            'title': f'Why {brand} exists',
                            'source': 'Promo',
                            'desc': 'Explain the product utility and audience.',
                            'matchedKeywords': [],
                        },
                        'platform': platform,
                        'mediaBrand': brand,
                        'sentiment': 'Neutral',
                        'modelKey': 'gpt',
                        'language': 'en',
                        'variantCount': 1,
                        'promoMode': True,
                    })
                    self.assertTrue(result['variants'], f'{brand}/{platform}')
                    self.assertEqual(result['hashtags'][0], BRAND_HASHTAGS[brand])
                    prompts = captured[start:]
                    self.assertTrue(prompts, f'{brand}/{platform}')
                    for prompt in prompts:
                        self.assertIn(f'promotional {platform} content for {brand}', prompt)
                        self.assertIn(_brand_doc(brand), prompt)


if __name__ == '__main__':
    unittest.main()
