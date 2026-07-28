import unittest

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


if __name__ == '__main__':
    unittest.main()
