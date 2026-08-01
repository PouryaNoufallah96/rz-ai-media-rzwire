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


if __name__ == '__main__':
    unittest.main()
