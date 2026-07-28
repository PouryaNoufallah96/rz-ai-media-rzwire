import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import chat_embeddings
import chat_faq_data
import chat_index
import chat_normalizer
import chat_storage
import database
from handlers import chat


class TemporaryChatDatabase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db_path = database.DB_PATH
        database.DB_PATH = Path(self.temp_dir.name) / 'chat-test.db'
        chat_storage._INITIALIZED_DB = None
        chat_index.reset_for_tests()
        database.init_db()
        chat_storage.ensure_tables()

    def tearDown(self):
        database.DB_PATH = self.original_db_path
        chat_storage._INITIALIZED_DB = None
        chat_index.reset_for_tests()
        self.temp_dir.cleanup()


class ChatPersistenceTests(TemporaryChatDatabase):
    def test_chat_expires_one_hour_after_last_message(self):
        database.add_chat_message(1, 'user', 'Old message')
        old_time = (datetime.now(timezone.utc) - timedelta(hours=1, minutes=1)).isoformat()
        connection = database._connect()
        try:
            connection.execute('UPDATE chat_messages SET created_at = ?', (old_time,))
            connection.commit()
        finally:
            connection.close()

        state = database.get_chat_state(1)

        self.assertEqual(state['messages'], [])
        self.assertIsNone(state['expiresAt'])

    def test_answer_metadata_is_preserved_in_history(self):
        database.add_chat_turn(
            1,
            'Question',
            'Answer',
            assistant_metadata={
                'answerSource': 'knowledge',
                'confidence': 'high',
                'sources': [{'id': 'source-1', 'title': 'Website guide'}],
                'knowledgeVersion': 'test-version',
                'tokenUsed': False,
            },
        )

        assistant = database.get_chat_state(1)['messages'][-1]

        self.assertEqual(assistant['answerSource'], 'knowledge')
        self.assertEqual(assistant['sources'][0]['id'], 'source-1')
        self.assertFalse(assistant['tokenUsed'])


class ChatNormalizerTests(unittest.TestCase):
    def test_corrects_common_english_transpositions_and_misspellings(self):
        result = chat_normalizer.understand('Hwo do I scedule a psot?')
        self.assertEqual(result['interpreted'], 'how do i schedule a post')
        self.assertEqual(result['confidence'], 'high')

    def test_maps_reviewed_phonetic_brand_alias(self):
        result = chat_normalizer.understand('What is Meta Game Coin?')
        self.assertEqual(result['interpreted'], 'what is meta games coin')
        self.assertEqual(result['corrections'][0]['kind'], 'phonetic')

    def test_ambiguous_short_word_is_not_silently_corrected(self):
        result = chat_normalizer.understand('cat')
        self.assertEqual(result['interpreted'], 'cat')
        self.assertEqual(result['corrections'], [])


class ChatRequestTests(TemporaryChatDatabase):
    def test_oversized_message_is_rejected_before_database_work(self):
        with patch.object(chat.database, 'get_chat_state') as state:
            with self.assertRaisesRegex(ValueError, 'characters or fewer'):
                chat.handle_chat(1, {
                    'message': 'x' * (chat.MAX_CHAT_MESSAGE_CHARS + 1),
                })
        state.assert_not_called()

    def test_approved_faq_never_uses_paid_tokens(self):
        result = chat.handle_chat(1, {
            'message': 'How does Analyze work?',
            'context': {'selectedMedia': ['Ranking Platform']},
        })

        self.assertFalse(result['tokenUsed'])
        self.assertEqual(result['answerSource'], 'faq')
        self.assertEqual(result['confidence'], 'high')
        self.assertEqual(result['knowledgeVersion'], chat.chat_knowledge.knowledge_version())
        self.assertTrue(result['sources'])

    def test_active_card_is_answered_deterministically(self):
        result = chat.handle_chat(1, {
            'message': 'What is on this card?',
            'context': {
                'selectedMedia': ['Ranking Platform'],
                'brand': 'Ranking Platform',
                'platform': 'telegram',
                'headline': 'ETF update',
                'copy': 'Reviewed card copy',
            },
        })

        self.assertEqual(result['answerSource'], 'context')
        self.assertIn('ETF update', result['reply'])
        self.assertFalse(result['tokenUsed'])

    @patch.object(chat.chat_policy, 'classify', return_value={'kind': 'allow', 'reply': ''})
    @patch.object(chat.chat_cache, 'lookup', return_value=None)
    @patch.object(chat.chat_index, 'retrieve')
    def test_reviewed_passage_replaces_external_llm_fallback(
        self, retrieve, _cache_lookup, _policy
    ):
        retrieve.return_value = [{
            'id': 'website-scheduling',
            'title': 'Website Guide',
            'section': 'Scheduling',
            'brand': '',
            'content': 'Use Preview to choose a future date and time.',
            'score': 0.84,
        }]

        result = chat.handle_chat(1, {
            'message': 'Explain the documented scheduling workflow in detail.',
            'context': {'selectedMedia': ['Ranking Platform']},
        })

        self.assertEqual(result['answerSource'], 'knowledge')
        self.assertEqual(result['confidence'], 'high')
        self.assertFalse(result['tokenUsed'])
        self.assertIn('future date and time', result['reply'])

    @patch.object(chat.chat_index, 'retrieve')
    def test_low_confidence_returns_closest_passage_with_warning(self, retrieve):
        retrieve.return_value = [{
            'id': 'closest',
            'title': 'Website Guide',
            'section': 'Preview',
            'brand': '',
            'content': 'The Preview panel contains the final review controls.',
            'score': 0.31,
        }]

        result = chat.handle_chat(1, {
            'message': 'Tell me the obscure documented workspace detail.',
            'context': {'selectedMedia': ['Ranking Platform']},
        })

        self.assertEqual(result['answerSource'], 'closest_passage')
        self.assertEqual(result['confidence'], 'low')
        self.assertIn('closest information', result['reply'])

    @patch.object(chat.chat_policy, 'classify', return_value={'kind': 'allow', 'reply': ''})
    @patch.object(chat.chat_cache, 'lookup', return_value=None)
    @patch.object(chat.chat_index, 'retrieve')
    def test_embedding_outage_can_return_bm25_passage(
        self, retrieve, _cache_lookup, _policy
    ):
        retrieve.return_value = [{
            'id': 'bm25',
            'title': 'Website Guide',
            'section': 'Analyze',
            'brand': '',
            'content': 'Analyze routes suitable stories to lanes.',
            'score': 0.30,
            'embeddingUsed': False,
        }]

        result = chat.handle_chat(1, {
            'message': 'Explain how stories are routed to lanes.',
            'context': {'selectedMedia': ['Ranking Platform']},
        })

        self.assertFalse(result['tokenUsed'])
        self.assertIn('routes suitable stories', result['reply'])

    def test_unrelated_question_is_rejected_locally(self):
        result = chat.handle_chat(1, {
            'message': 'What is the capital of France?',
            'context': {'selectedMedia': ['MGC Coin']},
        })

        self.assertEqual(result['answerSource'], 'policy')
        self.assertEqual(result['policy'], 'unrelated')
        self.assertFalse(result['tokenUsed'])

    def test_greeting_receives_a_friendly_local_reply(self):
        result = chat.handle_chat(1, {
            'message': 'Hi!',
            'context': {'selectedMedia': ['Ranking Platform']},
        })

        self.assertEqual(result['answerSource'], 'policy')
        self.assertEqual(result['policy'], 'small_talk')
        self.assertIn('How can I help', result['reply'])
        self.assertFalse(result['tokenUsed'])

    def test_persian_greeting_receives_a_friendly_local_reply(self):
        result = chat.handle_chat(1, {
            'message': 'سلام',
            'context': {'selectedMedia': ['Ranking Platform']},
        })

        self.assertEqual(result['policy'], 'small_talk')
        self.assertIn('دستیار', result['reply'])
        self.assertFalse(result['tokenUsed'])

    def test_handler_source_has_no_openrouter_dependency(self):
        source = Path(chat.__file__).read_text(encoding='utf-8').casefold()
        self.assertNotIn('openrouter', source)


class ApprovedFaqAcceptanceTests(TemporaryChatDatabase):
    def test_reviewed_bilingual_faq_queries(self):
        cases = []
        for faq in chat_faq_data.FAQ_SEEDS:
            question = faq['question']
            if faq['language'] == 'en':
                variants = [
                    question,
                    question.rstrip(' ?') + '   ?',
                    question.upper(),
                ]
            else:
                variants = [
                    question,
                    f'  {question}  ',
                    '  '.join(question.split()),
                ]
            cases.extend((variant, faq) for variant in variants)

        self.assertEqual(len(cases), len(chat_faq_data.FAQ_SEEDS) * 3)
        language_counts = {'en': 0, 'fa': 0}
        for question, expected in cases:
            with self.subTest(question=question):
                match = chat_storage.find_faq(
                    chat_storage.normalize_question(question),
                    expected['language'],
                )
                self.assertIsNotNone(match)
                self.assertEqual(match['answer'], expected['answer'])
                language_counts[expected['language']] += 1
        faq_language_counts = {
            language: sum(1 for faq in chat_faq_data.FAQ_SEEDS if faq['language'] == language) * 3
            for language in ('en', 'fa')
        }
        self.assertEqual(language_counts, faq_language_counts)


class EmbeddingClientTests(unittest.TestCase):
    def test_embedding_shape_is_strictly_validated(self):
        vector = chat_embeddings._extract_embedding([
            {'embedding': [0.0] * chat_embeddings.EMBEDDING_DIMENSION},
        ])
        self.assertEqual(len(vector), 768)

        with self.assertRaises(chat_embeddings.EmbeddingUnavailable):
            chat_embeddings._extract_embedding([{'embedding': [0.0] * 8}])

    def test_embedding_url_must_be_loopback(self):
        with patch.object(chat_embeddings, 'EMBEDDING_BASE_URL', 'https://example.com'):
            with self.assertRaises(chat_embeddings.EmbeddingUnavailable):
                chat_embeddings._validate_loopback()


class HybridIndexTests(TemporaryChatDatabase):
    def _chunks(self):
        return [
            {
                'id': 'one',
                'title': 'Website',
                'section': 'Scheduling',
                'brand': '',
                'language': 'en',
                'sourcePath': 'website.md',
                'content': 'Schedule a post from Preview.',
                'contentHash': 'hash-one',
            },
            {
                'id': 'two',
                'title': 'MGC Coin',
                'section': 'Brand',
                'brand': 'MGC Coin',
                'language': 'en',
                'sourcePath': 'mgc-coin.md',
                'content': 'MGC Coin gaming utility coverage.',
                'contentHash': 'hash-two',
            },
        ]

    def test_incremental_index_and_hybrid_ranking(self):
        first = [1.0] + [0.0] * 767
        second = [0.0, 1.0] + [0.0] * 766
        with (
            patch.object(chat_index.chat_knowledge, 'knowledge_chunks', return_value=self._chunks()),
            patch.object(chat_index.chat_knowledge, 'knowledge_version', return_value='version-1'),
            patch.object(
                chat_index.chat_embeddings,
                'embed_document',
                side_effect=[first, second],
            ) as embed_document,
        ):
            self.assertTrue(chat_index.sync_index())
            self.assertEqual(embed_document.call_count, 2)

        with (
            patch.object(chat_index.chat_embeddings, 'embed_query', return_value=second),
            patch.object(
                chat_index.chat_knowledge,
                'bm25_results',
                return_value=[{**self._chunks()[0], 'bm25Score': 1.0}],
            ),
        ):
            results = chat_index.retrieve('MGC Coin coverage', k=2)

        self.assertEqual(results[0]['id'], 'two')
        self.assertGreater(results[0]['semanticScore'], results[1]['semanticScore'])

        with (
            patch.object(chat_index.chat_knowledge, 'knowledge_chunks', return_value=self._chunks()),
            patch.object(chat_index.chat_knowledge, 'knowledge_version', return_value='version-1'),
            patch.object(chat_index.chat_embeddings, 'embed_document') as embed_document,
        ):
            self.assertTrue(chat_index.sync_index())
            embed_document.assert_not_called()

    def test_index_table_contains_traceable_metadata(self):
        vector = [1.0] + [0.0] * 767
        with (
            patch.object(chat_index.chat_knowledge, 'knowledge_chunks', return_value=self._chunks()[:1]),
            patch.object(chat_index.chat_knowledge, 'knowledge_version', return_value='version-1'),
            patch.object(chat_index.chat_embeddings, 'embed_document', return_value=vector),
        ):
            chat_index.sync_index()

        connection = sqlite3.connect(database.DB_PATH)
        try:
            row = connection.execute(
                'SELECT knowledge_version, section, source_path, embedding_dim '
                'FROM chat_knowledge_chunks WHERE id = ?',
                ('one',),
            ).fetchone()
        finally:
            connection.close()
        self.assertEqual(row, ('version-1', 'Scheduling', 'website.md', 768))


if __name__ == '__main__':
    unittest.main()




