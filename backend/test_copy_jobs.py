import time
import unittest
from unittest.mock import patch

from handlers.copy import handle_get_copy_job, handle_start_copy_job


class CopyGenerationJobTests(unittest.TestCase):
    def _wait_for_terminal_state(self, job_id):
        deadline = time.time() + 2
        while time.time() < deadline:
            job = handle_get_copy_job(job_id)
            if job['status'] in {'complete', 'failed'}:
                return job
            time.sleep(0.01)
        self.fail('Caption job did not finish in time')

    def test_completed_job_returns_original_copy_result(self):
        expected = {'variants': [{'copy': 'One'}, {'copy': 'Two'}, {'copy': 'Three'}]}
        with patch('handlers.copy.handle_generate_copy', return_value=expected):
            started = handle_start_copy_job({'variantCount': 3})
            finished = self._wait_for_terminal_state(started['jobId'])
        self.assertEqual(finished['status'], 'complete')
        self.assertEqual(finished['result'], expected)

    def test_failed_job_returns_clean_error(self):
        with patch('handlers.copy.handle_generate_copy', side_effect=RuntimeError('provider unavailable')):
            started = handle_start_copy_job({})
            finished = self._wait_for_terminal_state(started['jobId'])
        self.assertEqual(finished['status'], 'failed')
        self.assertEqual(finished['error'], 'provider unavailable')


if __name__ == '__main__':
    unittest.main()
