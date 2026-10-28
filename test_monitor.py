import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import monitor


class MonitorTests(unittest.TestCase):
    def test_baseline_does_not_email(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'state.json'
            with patch.object(monitor, 'fetch_posts', return_value=[{'id': '10'}]), patch.object(monitor, 'send_mail') as send:
                monitor.run(path)
                send.assert_not_called()
                self.assertEqual(monitor.json.loads(path.read_text())['since'], '10')

    def test_delivery_failure_is_retried_without_losing_posts(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'state.json'
            monitor.save(path, {'since': '10', 'pending': []})
            posts = [{'id': '11', 'text': 'hello', 'url': 'https://x.com/thsottiaux/status/11'}]
            with patch.object(monitor, 'fetch_posts', return_value=posts), patch.object(monitor, 'send_mail', side_effect=RuntimeError):
                with self.assertRaises(RuntimeError):
                    monitor.run(path)
            self.assertEqual(monitor.json.loads(path.read_text())['pending'], posts)
            with patch.object(monitor, 'fetch_posts', return_value=[]), patch.object(monitor, 'send_mail') as send:
                monitor.run(path)
                send.assert_called_once_with(posts)
            self.assertEqual(monitor.json.loads(path.read_text())['pending'], [])

    def test_bad_source_does_not_advance_state(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'state.json'
            monitor.save(path, {'since': '10', 'pending': []})
            original = path.read_bytes()
            with patch.object(monitor, 'fetch_posts', side_effect=ValueError):
                with self.assertRaises(ValueError):
                    monitor.run(path)
            self.assertEqual(path.read_bytes(), original)

    def test_pending_delivery_survives_source_outage(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'state.json'
            pending = [{'id': '11', 'text': 'hello', 'url': 'https://x.com/thsottiaux/status/11'}]
            monitor.save(path, {'since': '11', 'pending': pending})
            with patch.object(monitor, 'fetch_posts', side_effect=ValueError), patch.object(monitor, 'send_mail') as send:
                with self.assertRaises(ValueError):
                    monitor.run(path)
                send.assert_called_once_with(pending)
            self.assertEqual(monitor.json.loads(path.read_text()), {'since': '11', 'pending': []})

    def test_timeline_filters_context_reposts_and_paginates(self):
        def post(number, author=monitor.USER_ID, **extra):
            return {'id': str(number), 'author': {'id': author}, 'type': 'status', 'text': 'hello', **extra}
        pages = [
            {'results': [post(13), post(14, 'other'), post(12, reposted_by={})], 'cursor': {'bottom': 'next'}},
            {'results': [post(13), post(11), post(9)], 'cursor': {'bottom': None}},
        ]
        with patch.object(monitor, 'request', side_effect=pages):
            self.assertEqual([post['id'] for post in monitor.fetch_posts('10')], ['11', '13'])


if __name__ == '__main__':
    unittest.main()
