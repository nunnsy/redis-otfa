import time
import click
from redis import Redis, ResponseError
from constant import REQUEST_KEY


@click.command()
@click.option("--username", "-u", required=True)
@click.option("--password", "-p", required=True)
def connect(username: str, password: str):
    redis_connection = Redis(username=username, password=password)

    # TODO: Add heartbeat check for online status

    try:
        authed_user = redis_connection.acl_whoami()
        print(f"Authenticated: {authed_user}")
    except ResponseError:
        print("Wrong password or user does not exist - attempting user addition")

        redis_connection = Redis()
        redis_connection.xadd(name=REQUEST_KEY, fields={"username": username, "password": password}, id="*")

        time.sleep(1.0)

        redis_connection = Redis(username=username, password=password)

        try:
            print(f"Authenticated: {redis_connection.acl_whoami()}")
        except ResponseError:
            print("Wrong password")  # or the Python server is offline - note addition of heartbeat


if __name__ == "__main__":
    connect()
