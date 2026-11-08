"""Проверки opener без микрофона, запуска приложений и закрытия окон."""

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


PLUGIN_PATH = Path(__file__).resolve().parents[1] / 'plugins/opener/plugin.py'


class OpenerTests(unittest.TestCase):
    def setUp(self):
        self.vh = SimpleNamespace(
            query={}, say=Mock(), recognize_online=Mock(),
            normalize=lambda text: ' '.join(text.casefold().split()),
        )
        spec = importlib.util.spec_from_file_location(
            'tested_opener', PLUGIN_PATH,
        )
        self.plugin = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'core': SimpleNamespace(vh=self.vh)}):
            spec.loader.exec_module(self.plugin)

    def test_required_commands(self):
        cases = {
            'открой ютуб': ('open', 'website', 'youtube'),
            'запусти блокнот': ('open', 'program', 'notepad'),
            'закрой блокнот': ('close', 'program', 'notepad'),
            'открой гугл': ('open', 'website', 'google'),
            'открой файл main.py': ('open', 'file', 'main.py'),
            'открой папку Folder1': ('open', 'folder', 'Folder1'),
            'открой': ('open', None, None),
            'закрой': ('close', None, None),
            'не открывай блокнот': (None, None, None),
            'открой неизвестную программу': ('open', None, None),
            '  ОТКРОЙ   ЮТУБ  ': ('open', 'website', 'youtube'),
            'открой блокнт': ('open', 'program', 'notepad'),
            'открыть ютуба': ('open', 'website', 'youtube'),
            'открой файл блокнот.txt': ('open', 'file', 'блокнот.txt'),
            'открой папку "My Folder"': ('open', 'folder', 'My Folder'),
            'открой и закрой блокнот': (None, None, None),
            'открой ютуб и гугл': ('open', None, None),
            'открой папку файл': ('open', None, None),
            'открой файлообменник': ('open', None, None),
            'открой суперблокнот': ('open', None, None),
            '': (None, None, None),
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(self.plugin.parse_command(text), expected)

    def test_ambiguous_aliases(self):
        self.plugin.config['programs']['other'] = {
            'exe': 'other', 'aliases': ['блокнот'],
        }
        self.assertEqual(
            self.plugin.parse_command('открой блокнот'), ('open', None, None),
        )

    def test_questions(self):
        for name, answer, expected in [
            ('ask_action', 'закрой', 'close'),
            ('ask_type', 'сайт', 'website'),
            ('ask_type', 'программа', 'program'),
            ('ask_app_name', 'ютуб', 'youtube'),
            ('ask_app_name', 'Main.py', 'Main.py'),
            ('ask_app_name', '', None),
            ('ask_action', 'не открывай', None),
        ]:
            with self.subTest(name=name, answer=answer):
                self.vh.recognize_online.return_value = answer
                self.assertEqual(getattr(self.plugin, name)(), expected)

    def test_unrecognized_answer_does_not_reuse_old_query(self):
        self.vh.query['norm_text'] = 'открыть'
        self.vh.recognize_online.return_value = None
        self.assertIsNone(self.plugin.ask_action())

    def test_known_command_needs_no_questions(self):
        self.vh.query['norm_text'] = 'открой ютуб'
        with patch.object(self.plugin, 'open_app') as open_app:
            self.plugin.touch_app()
        open_app.assert_called_once_with('website', 'youtube')
        self.vh.recognize_online.assert_not_called()

    def test_explicit_arguments_have_priority(self):
        self.vh.query['norm_text'] = 'открой ютуб'
        with patch.object(self.plugin, 'close_app') as close_app:
            self.plugin.touch_app('close', 'program', 'notepad')
        close_app.assert_called_once_with('program', 'notepad')

    def test_missing_parameters_are_asked_once(self):
        self.vh.recognize_online.side_effect = [
            'открой', 'программа', 'блокнот',
        ]
        with patch.object(self.plugin, 'open_app') as open_app:
            self.plugin.touch_app()
        open_app.assert_called_once_with('program', 'notepad')
        self.assertEqual(self.vh.recognize_online.call_count, 3)

    def test_failed_clarification_does_not_execute(self):
        self.vh.recognize_online.return_value = ''
        with patch.object(self.plugin, 'open_app') as open_app:
            self.plugin.touch_app()
        open_app.assert_not_called()
        self.assertEqual(self.vh.recognize_online.call_count, 1)

    def test_negation_and_multiple_actions_do_not_execute(self):
        for text in ['не открывай блокнот', 'открой и закрой блокнот']:
            self.vh.query['norm_text'] = text
            with patch.object(self.plugin, 'open_app') as open_app:
                self.plugin.touch_app('open', 'program', 'notepad')
            open_app.assert_not_called()

    def test_open_website_reports_browser_failure(self):
        with patch.object(
            self.plugin.webbrowser, 'open', return_value=True,
        ) as op:
            self.assertTrue(self.plugin.open_app('website', 'youtube'))
        op.assert_called_once_with('https://www.youtube.com')
        with patch.object(self.plugin.webbrowser, 'open', return_value=False):
            with self.assertLogs('tested_opener', level='ERROR'):
                self.assertFalse(self.plugin.open_app('website', 'youtube'))

    def test_program_launch_and_failure(self):
        with patch.object(self.plugin.subprocess, 'Popen') as popen:
            self.assertTrue(self.plugin.open_app('program', 'notepad'))
        popen.assert_called_once_with(['notepad.exe'])
        with patch.object(
            self.plugin.subprocess, 'Popen', side_effect=OSError('missing'),
        ):
            with self.assertLogs('tested_opener', level='ERROR'):
                self.assertFalse(self.plugin.open_app('program', 'notepad'))

    def test_windows_search_types_name_and_keeps_trailing_space(self):
        for kind in ['file', 'folder']:
            for name in ['Main.py', 'Моя папка', None, '']:
                with self.subTest(kind=kind, name=name):
                    with patch.object(self.plugin.os, 'name', 'nt'):
                        with patch.object(self.plugin, 'keyboard') as keys:
                            with patch.object(self.plugin.time, 'sleep'):
                                self.assertTrue(
                                    self.plugin.open_app(kind, name)
                                )
                    self.assertEqual(keys.mock_calls, [
                        unittest.mock.call.send('windows'),
                        unittest.mock.call.write(f"{kind}: {name or ''}"),
                    ])

    def test_missing_file_name_starts_search_without_question(self):
        for kind, text in [('file', 'открой файл'), ('folder', 'открой папку')]:
            self.vh.query = {'norm_text': text}
            with patch.object(self.plugin, 'open_app') as open_app:
                self.plugin.touch_app()
            open_app.assert_called_once_with(kind, None)
        self.vh.recognize_online.assert_not_called()

    def test_search_reports_unsupported_platform_and_keyboard_error(self):
        with patch.object(self.plugin.os, 'name', 'posix'):
            with patch.object(self.plugin, 'keyboard') as keys:
                with self.assertLogs('tested_opener', level='ERROR'):
                    self.assertFalse(self.plugin.open_app('file', 'Main.py'))
            keys.send.assert_not_called()
        with patch.object(self.plugin.os, 'name', 'nt'):
            with patch.object(self.plugin.keyboard, 'send', side_effect=OSError):
                with self.assertLogs('tested_opener', level='ERROR'):
                    self.assertFalse(self.plugin.open_app('folder', None))

    def test_unsupported_closing_does_not_kill_processes(self):
        with patch.object(self.plugin.subprocess, 'run') as run:
            for kind in ['file', 'folder', 'website']:
                self.assertFalse(self.plugin.close_app(kind, 'anything'))
        run.assert_not_called()

    def test_windows_close_is_not_forced(self):
        with patch.object(self.plugin.os, 'name', 'nt'):
            with patch.object(self.plugin.subprocess, 'run') as run:
                self.assertTrue(self.plugin.close_app('program', 'notepad'))
        self.assertEqual(
            run.call_args.args[0], ['taskkill', '/IM', 'notepad.exe'],
        )

    def test_windows_close_failure(self):
        error = subprocess.CalledProcessError(
            1, ['taskkill'], stderr=b'not found',
        )
        with patch.object(self.plugin.os, 'name', 'nt'):
            with patch.object(
                self.plugin.subprocess, 'run', side_effect=error,
            ):
                with self.assertLogs('tested_opener', level='ERROR'):
                    self.assertFalse(
                        self.plugin.close_app('program', 'notepad')
                    )

    def test_posix_only_closes_owned_program(self):
        with patch.object(self.plugin.os, 'name', 'posix'):
            self.assertFalse(self.plugin.close_app('program', 'notepad'))
            process = Mock()
            process.poll.return_value = None
            self.plugin.started_programs['notepad'] = process
            self.assertTrue(self.plugin.close_app('program', 'notepad'))
            process.terminate.assert_called_once()
            process.wait.assert_called_once_with(timeout=3)
            self.assertNotIn('notepad', self.plugin.started_programs)

    def test_missing_corrupt_and_invalid_config(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / 'config.json'
            self.plugin.config_path = path
            with self.assertLogs('tested_opener', level='ERROR'):
                self.assertEqual(self.plugin.load_config(), {})
                path.write_text('{broken')
                self.assertEqual(self.plugin.load_config(), {})
                path.write_text(json.dumps({
                    'programs': {'bad': 'old format'},
                }))
                self.assertEqual(self.plugin.load_config(), {})

    def test_raw_file_path_survives_query_normalization(self):
        self.vh.query.update({
            'norm_text': 'открыть файл mainpy',
            'text': 'открой файл Main.py',
        })
        self.vh.normalize = lambda text: 'открыть файл mainpy'
        with patch.object(self.plugin, 'open_app') as open_app:
            self.plugin.touch_app()
        open_app.assert_called_once_with('file', 'Main.py')

    def test_close_timeout_does_not_force_kill(self):
        process = Mock()
        process.poll.return_value = None
        process.wait.side_effect = subprocess.TimeoutExpired('notepad', 3)
        self.plugin.started_programs['notepad'] = process
        with patch.object(self.plugin.os, 'name', 'posix'):
            with self.assertLogs('tested_opener', level='ERROR'):
                self.assertFalse(self.plugin.close_app('program', 'notepad'))
        process.kill.assert_not_called()

    def test_intent_handler(self):
        self.assertIs(
            self.plugin.intents['touch_app']['cmd'], self.plugin.touch_app,
        )


if __name__ == '__main__':
    unittest.main()
