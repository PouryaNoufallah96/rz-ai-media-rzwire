import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import database


class SavedCardImageTests(unittest.TestCase):
    def test_saved_card_preserves_approved_image_for_later_scheduling(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / 'saved-card-test.db'
            with patch.object(database, 'DB_PATH', db_path):
                database.init_db()
                conn = database._connect()
                try:
                    cursor = conn.execute(
                        'INSERT INTO users (username, email, password_hash, created_at) VALUES (?, ?, ?, ?)',
                        ('analytics-user', 'analytics@example.com', 'hash', database._now_iso()),
                    )
                    user_id = cursor.lastrowid
                    conn.commit()
                finally:
                    conn.close()

                saved_id = database.create_saved_card(user_id, {
                    'id': 'analytics-mgc-30d',
                    'media': 'MGC Coin',
                    'platform': 'X',
                    'headline': 'MGC vs BTC',
                    'copy': 'Verified market comparison.',
                    'hashtags': ['#MGC'],
                    'imageB64': 'approved-image-base64',
                })

                saved = database.get_saved_card(saved_id, user_id)
                self.assertEqual(saved['image_b64'], 'approved-image-base64')
                self.assertEqual(saved['platform'], 'X')


if __name__ == '__main__':
    unittest.main()
