import unittest
from unittest.mock import patch

from config import OPENROUTER_IMAGE_MODELS
from handlers.image import handle_generate_image


class ImageModelAllowlistTests(unittest.TestCase):
    def test_only_approved_image_models_are_available(self):
        self.assertEqual(set(OPENROUTER_IMAGE_MODELS), {
            'openai/gpt-5.4-image-2',
            'google/gemini-3.1-flash-image-preview',
            'google/gemini-3-pro-image-preview',
            'recraft/recraft-v4-pro',
        })

    def test_unknown_image_model_is_rejected_before_generation(self):
        with self.assertRaisesRegex(ValueError, 'Unsupported image generation model'):
            handle_generate_image({'model': 'vendor/removed-image-model'})

    @patch('handlers.image.openrouter_image')
    def test_analytics_composition_requires_and_forwards_two_locked_references(self, generate):
        generate.return_value = ('image-data', 'openai/gpt-5.4-image-2')
        references = ['data:image/png;base64,layout', 'data:image/png;base64,chart']

        result = handle_generate_image({
            'model': 'openai/gpt-5.4-image-2',
            'mediaBrand': 'MGC Coin',
            'compositionMode': 'analytics_post',
            'referenceImages': references,
            'copy': 'MGC, OASIS, and BTC verified comparison.',
        })

        self.assertEqual(result['imageB64'], 'image-data')
        self.assertEqual(generate.call_args.kwargs['ref_images'], references)
        self.assertIn('FIRST image', generate.call_args.args[0])
        self.assertIn('SECOND image', generate.call_args.args[0])

    def test_analytics_composition_rejects_missing_chart_reference(self):
        with self.assertRaisesRegex(ValueError, 'design reference and an approved chart'):
            handle_generate_image({
                'compositionMode': 'analytics_post',
                'referenceImages': ['data:image/png;base64,layout'],
            })

    @patch('handlers.image.openrouter_image')
    def test_analytics_background_forwards_three_locked_references(self, generate):
        generate.return_value = ('background-data', 'openai/gpt-5.4-image-2')
        references = [
            'data:image/png;base64,design',
            'data:image/png;base64,composition',
            'data:image/png;base64,chart',
        ]

        result = handle_generate_image({
            'model': 'openai/gpt-5.4-image-2',
            'mediaBrand': 'MGC Coin',
            'compositionMode': 'analytics_background',
            'templateId': 'phone',
            'brandTheme': 'mgc',
            'outputDimensions': {'width': 1080, 'height': 1350},
            'seriesMetadata': [{'symbol': 'MGC'}, {'symbol': 'BTC'}],
            'referenceImages': references,
        })

        self.assertEqual(result['imageB64'], 'background-data')
        self.assertEqual(result['compositionMode'], 'analytics_background')
        self.assertEqual(generate.call_args.kwargs['ref_images'], references)
        prompt = generate.call_args.args[0]
        self.assertIn('REFERENCE 1', prompt)
        self.assertIn('REFERENCE 2', prompt)
        self.assertIn('REFERENCE 3', prompt)
        self.assertIn('STRICTLY FORBIDDEN', prompt)

    def test_analytics_background_rejects_incomplete_payload(self):
        with self.assertRaisesRegex(ValueError, 'exactly three ordered references'):
            handle_generate_image({
                'compositionMode': 'analytics_background',
                'templateId': 'phone',
                'seriesMetadata': [{'symbol': 'MGC'}],
                'referenceImages': ['design', 'chart'],
            })

    @patch('handlers.image.openrouter_image')
    def test_frame_composite_forwards_static_frame_and_verified_chart(self, generate):
        generate.return_value = ('finished-post', 'openai/gpt-5.4-image-2')
        references = [
            'data:image/png;base64,static-frame',
            'data:image/png;base64,verified-chart',
        ]

        result = handle_generate_image({
            'model': 'openai/gpt-5.4-image-2',
            'mediaBrand': 'MGC Coin',
            'compositionMode': 'analytics_frame_composite',
            'templateId': 'laptop',
            'brandTheme': 'mgc',
            'outputDimensions': {'width': 1080, 'height': 1350},
            'seriesMetadata': [{'symbol': 'MGC'}, {'symbol': 'BTC'}],
            'referenceImages': references,
            'headline': 'MGC outperformed BTC over 30 days',
            'supportingText': 'Verified market movement, presented clearly.',
        })

        self.assertEqual(result['imageB64'], 'finished-post')
        self.assertEqual(result['compositionMode'], 'analytics_frame_composite')
        self.assertEqual(generate.call_args.kwargs['ref_images'], references)
        prompt = generate.call_args.args[0]
        self.assertIn('REFERENCE 1', prompt)
        self.assertIn('REFERENCE 2', prompt)
        self.assertIn('reserved chart aperture', prompt)
        self.assertIn('fake CoinMarketCap screenshot', prompt)

    def test_frame_composite_rejects_incomplete_payload(self):
        with self.assertRaisesRegex(ValueError, 'exactly two ordered references'):
            handle_generate_image({
                'compositionMode': 'analytics_frame_composite',
                'templateId': 'laptop',
                'seriesMetadata': [{'symbol': 'MGC'}],
                'referenceImages': ['static-frame'],
            })


if __name__ == '__main__':
    unittest.main()
