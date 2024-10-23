import logging
import time
from threading import Thread
from typing import Sequence

from redis import Redis
from redis.client import Pipeline

from redis_otfa.constants import REQUEST_KEY, USERS_KEY
from redis_otfa.core import does_user_exist

_LOGGER = logging.getLogger()


class OtfaHandler:

    def __init__(
        self,
        redis_connection: Redis,
        admin_username: str,
        admin_password: str,
        user_commands: Sequence[str] | None = None,
        user_keys: Sequence[str] | None = None,
        user_channels: Sequence[str] | None = None,
    ) -> None:
        """
        Instantiate the handler

        Args:
            redis_connection (Redis): Redis connection instance
            admin_username (str): Administrator username (needs ACL permissions)
            admin_password (str): Administrator password
            user_commands (Sequence[str] | None, optional): User commands to allow. Defaults to None.
            user_keys (Sequence[str] | None, optional): User keys to allow. Use `{username}` within the string for user-specific keys. Defaults to None.
            user_channels (Sequence[str] | None, optional): User channels to allow. Use `{username}` within the string for user-specific channels. Defaults to None.
        """
        self._redis_connection = redis_connection

        self._redis_connection.auth(username=admin_username, password=admin_password)

        self._running: bool = False
        self._request_index: bytes = b"0"
        self._loop_thread: Thread | None = None

        self._user_commands: Sequence[str] | None = user_commands
        self._user_keys: Sequence[str] | None = user_keys
        self._user_channels: Sequence[str] | None = user_channels

    def run(self):
        _LOGGER.info("Starting handler thread")
        self._running = True
        self._loop_thread = Thread(target=self._loop, daemon=True)
        self._loop_thread.start()

    def stop(self):
        _LOGGER.info("Stopping handler thread")
        if self._loop_thread is None:
            raise RuntimeError("Cannot stop the handler thread when it is not running")
        self._running = False
        self._loop_thread.join()

    def _loop(self) -> None:
        _LOGGER.info("Handler thread started")
        while self._running:
            next_request = self._redis_connection.xread(count=1, streams={REQUEST_KEY: self._request_index})
            if len(next_request) == 1:
                _LOGGER.debug("New request: %s", next_request)
                # [[b'otfa_request', [(b'1728918841791-0', {b'username': b'user', b'password': b'pass'})]]]
                next_request = next_request[0][1][0]
                next_request_id: bytes = next_request[0]
                next_request_data: dict = next_request[1]

                if (b"username" not in next_request_data) or (b"password" not in next_request_data):
                    _LOGGER.error("Malformed request, username or password is missing - raw request: %s", next_request)
                    continue

                username_raw: bytes = next_request_data[b"username"]
                password_raw: bytes = next_request_data[b"password"]
                username: str = username_raw.decode()
                password: str = password_raw.decode()

                user_exists: bool = does_user_exist(self._redis_connection, username)

                if not user_exists:
                    # User does not exist, and we can add them
                    _LOGGER.info("Registering new user: %s", username)
                    registration_pipeline: Pipeline = self._redis_connection.pipeline()

                    user_commands: Sequence[str] | None = self._user_commands
                    user_keys: Sequence[str] | None = (
                        None if self._user_keys is None else [uk.format(username=username) for uk in self._user_keys]
                    )
                    user_channels: Sequence[str] | None = (
                        None
                        if self._user_channels is None
                        else [uc.format(username=username) for uc in self._user_channels]
                    )

                    registration_pipeline.acl_setuser(
                        username=username,
                        enabled=True,
                        passwords=[f"+{password}"],
                        reset=True,
                        commands=user_commands,
                        keys=user_keys,
                        channels=user_channels,
                    )
                    registration_pipeline.sadd(USERS_KEY, username)

                    registration_pipeline.execute()

                self._request_index = next_request_id

            time.sleep(0.001)
