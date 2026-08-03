import math
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

import numpy as np

from filtering import pipeline
from handlers import editorial


class _FakeEmbedder:
    def __init__(self, vectors):
        self.vectors = np.asarray(vectors, dtype=np.float32)

    def embed(self, texts):
        return self.vectors[:len(texts)], 1, 0


def _articles(count):
    published = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    return [
        {
            'title': f'Article {index}',
            'desc': f'Unique report number {index}',
            'source': 'CoinDesk',
            'link': f'https://example.com/news/{index}',
            'pubDate': published,
        }
        for index in range(count)
    ]


class EmbeddingPipelineMinimumTests(unittest.TestCase):
    def _run(self, vectors):
        anchors = {
            'mgc_coin': np.asarray([[1.0, 0.0]], dtype=np.float32),
            'ranking_platform': np.asarray([[0.0, 1.0]], dtype=np.float32),
        }
        with (
            patch.object(pipeline, '_get_embedder', return_value=_FakeEmbedder(vectors)),
            patch.object(pipeline, '_get_anchor_vecs', return_value=anchors),
            patch.object(pipeline, '_get_topic_vec', return_value=None),
        ):
            return pipeline.run_pipeline(
                _articles(len(vectors)),
                ['MGC Coin', 'Ranking Platform'],
                '',
                24,
            )

    def test_each_brand_gets_its_ten_highest_embedding_matches(self):
        vectors = np.asarray([
            [math.cos(2 * math.pi * index / 12),
             math.sin(2 * math.pi * index / 12)]
            for index in range(12)
        ], dtype=np.float32)

        result = self._run(vectors)
        by_brand = {
            brand: {
                int(item['title'].split()[-1])
                for item in result['shortlist']
                if brand in item['_brands']
            }
            for brand in ('MGC Coin', 'Ranking Platform')
        }

        expected_mgc = set(sorted(range(12), key=lambda i: vectors[i][0], reverse=True)[:10])
        expected_ranking = set(sorted(range(12), key=lambda i: vectors[i][1], reverse=True)[:10])
        self.assertEqual(by_brand['MGC Coin'], expected_mgc)
        self.assertEqual(by_brand['Ranking Platform'], expected_ranking)
        self.assertEqual(result['stats']['brand_mgc_coin'], 10)
        self.assertEqual(result['stats']['brand_ranking_platform'], 10)

    def test_semantic_clustering_does_not_reduce_brand_below_ten(self):
        vectors = np.asarray([[1.0, 0.0]] * 12, dtype=np.float32)

        result = self._run(vectors)

        for brand in ('MGC Coin', 'Ranking Platform'):
            count = sum(brand in item['_brands'] for item in result['shortlist'])
            self.assertEqual(count, 10)
        self.assertEqual(result['stats']['dropped_clustered'], 2)

    def test_smaller_source_pool_sends_every_available_article(self):
        vectors = np.asarray([
            [math.cos(2 * math.pi * index / 7),
             math.sin(2 * math.pi * index / 7)]
            for index in range(7)
        ], dtype=np.float32)

        result = self._run(vectors)

        self.assertEqual(result['stats']['brand_mgc_coin'], 7)
        self.assertEqual(result['stats']['brand_ranking_platform'], 7)

    def test_every_selected_editor_receives_ten_candidates_per_brand(self):
        vectors = np.asarray([
            [math.cos(2 * math.pi * index / 12),
             math.sin(2 * math.pi * index / 12)]
            for index in range(12)
        ], dtype=np.float32)
        result = self._run(vectors)
        prompts = {}

        def fake_editorial_call(model_key, _cfg, system_prompt, user_prompt):
            prompts[model_key] = (system_prompt, user_prompt)
            return model_key, {'brands': {}}

        body = {
            'shortlist': result['shortlist'],
            'selectedMedia': ['MGC Coin', 'Ranking Platform'],
            'selectedPlatforms': ['X'],
            'selectedModels': ['gpt', 'deepseek'],
            'topics': '',
            'testMode': False,
            'enrichArticles': False,
            'language': 'en',
        }
        with (
            patch.object(editorial, 'OPENROUTER_KEY', 'test-key'),
            patch.object(editorial, '_editorial_call_one', side_effect=fake_editorial_call),
        ):
            responses = list(editorial.handle_editorial_select(body))

        self.assertEqual(len(responses), 2)
        self.assertEqual(set(prompts), {'gpt', 'deepseek'})
        for system_prompt, user_prompt in prompts.values():
            self.assertIn("10 embedding-ranked eligible candidates", system_prompt)
            self.assertEqual(user_prompt.count('MGC Coin ('), 10)
            self.assertEqual(user_prompt.count('Ranking Platform ('), 10)


if __name__ == '__main__':
    unittest.main()
