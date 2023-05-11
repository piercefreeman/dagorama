import time
from subprocess import Popen

from click import command, secho, option
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


class EventHandler(FileSystemEventHandler):
    def __init__(self):
        super().__init__()

        # Bootup an initial version before files change
        self.current_worker = self.new_worker()

    def dispatch(self, event):
        if event.event_type not in {"modified", "created"}:
            return None

        if self.current_worker:
            self.current_worker.terminate()
            self.current_worker = None

        self.current_worker = self.new_worker()
        secho(
            f"[{time.asctime()}] noticed: [{event.event_type}] on: [{event.src_path}]",
            fg="blue",
        )

    def new_worker(self):
        return Popen(
            "echo 'Rebooting worker...' && poetry run worker",
            shell=True
        )


@command()
@option("--watch-dir", default=".", help="Directory to watch for changes")
def run_hot_reload_worker(watch_dir):
    """
    Run the dagorama worker, listening to changes in a directory. This should just be
    used for development purposes.

    """
    secho(f"Launching a dagorama worker in hot-reload mode. This is only intended for development purposes.", fg="yellow")

    event_handler = EventHandler()

    observer = Observer()
    observer.schedule(event_handler, watch_dir, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    finally:
        observer.stop()
        observer.join()
