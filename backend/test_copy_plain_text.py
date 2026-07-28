import unittest

from handlers.copy import _plain_social_copy
from handlers.social import _strip_markdown_markers


class PlainSocialCopyTests(unittest.TestCase):
    def test_generated_copy_never_keeps_asterisk_markdown(self):
        source = '**Charles Schwab Backs Crypto Clarity Act** Charles Schwab *supports* action.'
        self.assertEqual(
            _plain_social_copy(source),
            'Charles Schwab Backs Crypto Clarity Act Charles Schwab supports action.',
        )

    def test_publish_sanitizer_removes_paired_and_unpaired_stars(self):
        self.assertEqual(
            _strip_markdown_markers('**Headline** with *emphasis and a stray *'),
            'Headline with emphasis and a stray',
        )


if __name__ == '__main__':
    unittest.main()
