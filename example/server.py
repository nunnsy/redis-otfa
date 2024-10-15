import logging
import time

import click
from redis import Redis

from redis_otfa import OtfaHandler


@click.command()
@click.option("--username", "-u", required=True)
@click.option("--password", "-p", required=True)
@click.option("--redis-host", required=True, default="localhost")
@click.option("--redis-port", required=True, default=6379)
def connect(username: str, password: str, redis_host: str, redis_port: int):

    logging.basicConfig(level=logging.DEBUG)

    # Connect as default user
    redis_connection = Redis(host=redis_host, port=redis_port)

    otfa_handler = OtfaHandler(redis_connection, username, password)

    otfa_handler.run()

    while (command := input()) != "exit":
        time.sleep(0.1)

    otfa_handler.stop()


if __name__ == "__main__":
    connect()
