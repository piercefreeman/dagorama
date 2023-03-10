from click import command, option

from dagorama.runner import execute_worker


@command()
@option("--exclude-queue", multiple=True)
@option("--include-queue", multiple=True)
@option("--toleration", multiple=True)
def worker(exclude_queue: list[str], include_queue: list[str], toleration: list[str]):
    execute_worker(
        exclude_queues=exclude_queue,
        include_queues=include_queue,
        queue_tolerations=toleration,
    )
