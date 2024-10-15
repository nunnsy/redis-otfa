import click
from redis import Redis

from redis_otfa import authenticate


@click.command()
@click.option("--username", "-u", required=True)
@click.option("--password", "-p", required=True)
@click.option("--redis-host", required=True, default="localhost")
@click.option("--redis-port", required=True, default=6379)
def connect(username: str, password: str, redis_host: str, redis_port: int):

    # Connect as default user
    redis_connection = Redis(host=redis_host, port=redis_port)

    authenticate(redis_connection, username, password)


if __name__ == "__main__":
    connect()
