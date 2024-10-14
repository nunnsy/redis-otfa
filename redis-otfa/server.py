from threading import Thread
import time
from redis import Redis
from constant import REQUEST_KEY


class AuthServer:

    def __init__(self):
        print(f"Connecting to localhost:6379 with admin:admin")
        self._redis_connection = Redis(host="localhost", port=6379, username="admin", password="admin")
        self._running: bool = False
        self._auth_index: bytes = b"0"
        self._loop_thread: Thread | None = None

    def run(self):
        print("Starting auth thread")
        self._running: bool = True
        self._loop_thread = Thread(target=self._loop, daemon=True)
        self._loop_thread.start()

    def stop(self):
        print("Stopping auth thread")
        if self._loop_thread is None:
            raise RuntimeError("Cannot stop the auth server when it is not running")
        self._running = False
        self._loop_thread.join()

    def _loop(self):
        print("Entering loop")
        while self._running:
            next_request = self._redis_connection.xread(count=1, streams={REQUEST_KEY: self._auth_index})
            if len(next_request) == 1:
                print(f"New request: {next_request}")
                # [[b'otfa_request', [(b'1728918841791-0', {b'username': b'user', b'password': b'pass'})]]]
                next_request = next_request[0][1][0]
                next_request_id: bytes = next_request[0]
                next_request_data: dict = next_request[1]
                next_request_username_raw: bytes = next_request_data[b"username"]
                next_request_password_raw: bytes = next_request_data[b"password"]
                next_request_username: str = next_request_username_raw.decode()
                next_request_password: str = next_request_password_raw.decode()

                user_query: bytes | None = self._redis_connection.acl_getuser(next_request_username)

                if user_query is None:
                    # User does not exist, and we can add them
                    print(f"Added new user: {next_request_username}")
                    self._redis_connection.acl_setuser(
                        username=next_request_username,
                        enabled=True,
                        passwords=[f"+{next_request_password}"],
                        commands=["+ACL|WHOAMI"],
                    )

                self._auth_index = next_request_id

            time.sleep(0.001)


if __name__ == "__main__":
    print("AuthServer Example")
    auth_server: AuthServer = AuthServer()
    auth_server.run()
    while True:
        time.sleep(1)
