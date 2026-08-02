import time
import unittest
from unittest.mock import patch

from handlers.image import handle_get_image_job, handle_start_image_job


class ImageGenerationJobTests(unittest.TestCase):
    def _wait_for_terminal_state(self, job_id):
        deadline = time.time() + 2
        while time.time() < deadline:
            job = handle_get_image_job(job_id)
            if job['status'] in {'complete', 'failed'}:
                return job
            time.sleep(0.01)
        self.fail('Image job did not finish in time')

    def test_completed_job_returns_original_image_result(self):
        expected = {'imageB64': 'abc123', 'model': 'image-model'}
        with patch('handlers.image.handle_generate_image', return_value=expected):
            started = handle_start_image_job({'compositionMode': 'analytics_art_directed'})
            finished = self._wait_for_terminal_state(started['jobId'])
        self.assertEqual(finished['status'], 'complete')
        self.assertEqual(finished['result'], expected)

    def test_failed_job_returns_clean_error(self):
        with patch('handlers.image.handle_generate_image', side_effect=RuntimeError('upstream unavailable')):
            started = handle_start_image_job({})
            finished = self._wait_for_terminal_state(started['jobId'])
        self.assertEqual(finished['status'], 'failed')
        self.assertEqual(finished['error'], 'upstream unavailable')


if __name__ == '__main__':
    unittest.main()
