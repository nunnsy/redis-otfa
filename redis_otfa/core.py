from redis import AuthenticationError, Redis
from tenacity import RetryError, Retrying, retry_if_exception_type, stop_after_attempt, wait_fixed

from redis_otfa.constants import REQUEST_KEY, USERS_KEY


class PasswordError(Exception):
    pass


class UserDoesNotExistError(Exception):
    pass


class RegistrationError(Exception):
    pass


def does_user_exist(redis_connection: Redis, username: str) -> bool:
    return redis_connection.sismember(USERS_KEY, username)


def register_user(redis_connection: Redis, username: str, password: str):
    redis_connection.xadd(name=REQUEST_KEY, fields={"username": username, "password": password}, id="*")


def authenticate(
    redis_connection: Redis,
    username: str,
    password: str,
    retry_policy: Retrying = Retrying(
        stop=stop_after_attempt(5), wait=wait_fixed(0.01), retry=retry_if_exception_type(UserDoesNotExistError)
    ),
):

    user_exists: bool = does_user_exist(redis_connection, username)

    if user_exists:
        try:
            redis_connection.auth(username=username, password=password)
            return
        except AuthenticationError as authentication_error:
            raise PasswordError("Incorrect password") from authentication_error

    register_user(redis_connection, username, password)

    try:
        for attempt in retry_policy:
            with attempt:
                user_exists = redis_connection.sismember(USERS_KEY, username)
                if not user_exists:
                    raise UserDoesNotExistError
    except RetryError:
        raise RegistrationError(
            "Unable to register user (user does not exist after exhausting retry policy). "
            "Is the authentication server online?"
        )

    try:
        redis_connection.auth(username=username, password=password)
        return
    except AuthenticationError as authentication_error:
        raise RegistrationError(
            "Incorrect password after registration, likely due another client registering the user first"
        ) from authentication_error
