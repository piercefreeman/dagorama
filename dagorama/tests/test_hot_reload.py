from subprocess import Popen
from time import sleep
from unittest.mock import ANY, MagicMock, call, patch

from click.testing import CliRunner
from watchdog.events import FileSystemEvent

from dagorama.hot_reload import EventHandler, Observer, run_hot_reload_worker

REBOOT_COMMAND = "echo 'Rebooting worker...' && poetry run worker"


def test_dispatch():
    event = MagicMock(spec=FileSystemEvent)
    event.event_type = "modified"
    Popen_mock = MagicMock(spec=Popen)

    with patch("dagorama.hot_reload.Popen", new=Popen_mock):
        handler = EventHandler()
        handler.current_worker = Popen_mock.return_value
        handler.dispatch(event)

        # Assert that the current_worker has been terminated and a new one has been created
        assert Popen_mock.return_value.terminate.call_args_list == [call()]
        assert Popen_mock.call_args_list == [
            call(REBOOT_COMMAND, shell=True),
            call(REBOOT_COMMAND, shell=True),
        ]


def test_new_worker():
    Popen_mock = MagicMock(spec=Popen)

    with patch("dagorama.hot_reload.Popen", new=Popen_mock):
        handler = EventHandler()

        # Should boot up and auto-init a new worker
        assert Popen_mock.call_args_list == [call(REBOOT_COMMAND, shell=True)]

        worker = handler.new_worker()

        # Assert that a new process has been created
        # One on init and one on dispatch
        assert worker == Popen_mock.return_value
        assert Popen_mock.call_args_list == [
            call(REBOOT_COMMAND, shell=True),
            call(REBOOT_COMMAND, shell=True),
        ]


def test_run_hot_reload_worker():
    Observer_mock = MagicMock(spec=Observer)

    with patch("dagorama.hot_reload.Observer", new=Observer_mock), patch(
        "time.sleep", side_effect=Exception("Stop loop")
    ):
        runner = CliRunner()
        result = runner.invoke(run_hot_reload_worker, ["--watch-dir", "TEST_DIR"])

        # Assert that an observer has been set up and started
        assert Observer_mock.return_value.schedule.call_args_list == [
            call(ANY, "TEST_DIR", recursive=True)
        ]
        assert Observer_mock.return_value.start.call_args_list == [call()]

        # Assert that there was an exception raised to stop the loop
        assert result.exit_code == 1
        assert "Stop loop" in str(result.exception)


def test_file_creation_triggers_dispatch(tmp_path):
    # Mocking Popen
    Popen_mock = MagicMock(spec=Popen)

    with patch("dagorama.hot_reload.Popen", new=Popen_mock):
        handler = EventHandler()

        # Setup observer for the temporary directory
        observer = Observer()
        observer.schedule(handler, str(tmp_path), recursive=True)
        observer.start()

        # Create a new file in the temporary directory
        new_file = tmp_path / "new_file.txt"
        new_file.write_text("Hello, World!")

        # Sleep for a moment to let the observer detect the file change
        sleep(1)

        # Assert that the current_worker has been terminated and a new one has been created
        # One alert for the initial file creation, one for folder modification, and one for the file modification
        # We mostly care that it got more than one alert
        reboot_count = len(Popen_mock.return_value.terminate.call_args_list)
        assert reboot_count >= 1
        # Initial launch plus reboots
        assert Popen_mock.call_args_list == [call(REBOOT_COMMAND, shell=True)] * (
            reboot_count + 1
        )

        observer.stop()
        observer.join()
