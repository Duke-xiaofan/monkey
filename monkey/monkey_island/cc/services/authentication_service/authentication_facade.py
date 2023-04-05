import string
import time
from threading import Lock
from typing import Sequence, Tuple

from flask_security import UserDatastore

from common.types import OTP
from common.utils.code_utils import secure_generate_random_string
from monkey_island.cc.event_queue import IIslandEventQueue, IslandEventTopic
from monkey_island.cc.models import IslandMode
from monkey_island.cc.repositories import UnknownRecordError
from monkey_island.cc.server_utils.encryption import ILockableEncryptor
from monkey_island.cc.services.authentication_service.token_generator import TokenGenerator

from . import AccountRole
from .i_otp_repository import IOTPRepository
from .token_parser import ParsedToken, TokenParser
from .types import Token
from .user import User

OTP_EXPIRATION_TIME = 2 * 60  # 2 minutes


class AuthenticationFacade:
    """
    A service for user authentication
    """

    def __init__(
        self,
        repository_encryptor: ILockableEncryptor,
        island_event_queue: IIslandEventQueue,
        user_datastore: UserDatastore,
        token_generator: TokenGenerator,
        token_parser: TokenParser,
        otp_repository: IOTPRepository,
    ):
        self._repository_encryptor = repository_encryptor
        self._island_event_queue = island_event_queue
        self._datastore = user_datastore
        self._token_generator = token_generator
        self._token_parser = token_parser
        self._otp_repository = otp_repository
        self._otp_read_lock = Lock()

    def needs_registration(self) -> bool:
        """
        Checks if a user is already registered on the Island

        :return: Whether registration is required on the Island
        """
        island_api_user_role = self._datastore.find_or_create_role(
            name=AccountRole.ISLAND_INTERFACE.name
        )
        return not self._datastore.find_user(roles=[island_api_user_role])

    def remove_user(self, username: str):
        """
        Unregisters a user, removing all tokens in the process

        :param username: Username of the user to unregister
        """
        user = self._datastore.find_user(username=username)
        if user is not None:
            self.revoke_all_tokens_for_user(user)  # Redundant?
            self._datastore.delete_user(user)

    def revoke_all_tokens_for_user(self, user: User):
        """
        Revokes all tokens for a specific user
        """
        self._datastore.set_uniquifier(user)

    def revoke_all_tokens_for_all_users(self):
        """
        Revokes all tokens for all users
        """
        for user in User.objects:
            self.revoke_all_tokens_for_user(user)

    def generate_new_token_pair(self, refresh_token: Token) -> Tuple[Token, Token]:
        """
        Generates a new access token and refresh, given a valid refresh token

        :param refresh_token: Refresh token
        :raise TokenValidationError: If the refresh token is invalid or expired
        :return: Tuple of the new access token and refresh token
        """
        parsed_refresh_token = self._token_parser.parse(refresh_token)
        user = self._get_refresh_token_owner(parsed_refresh_token)

        new_access_token = user.get_auth_token()
        new_refresh_token = self._token_generator.generate_token(user.fs_uniquifier)

        return new_access_token, new_refresh_token

    def _get_refresh_token_owner(self, refresh_token: ParsedToken) -> User:
        user = self._datastore.find_user(fs_uniquifier=refresh_token.user_uniquifier)
        if not user:
            raise Exception("Invalid refresh token")
        return user

    def generate_otp(self) -> OTP:
        """
        Generates a new OTP

        The generated OTP is saved to the `IOTPRepository`
        """
        otp = OTP(secure_generate_random_string(32, string.ascii_letters + string.digits + "._-"))
        expiration_time = time.monotonic() + OTP_EXPIRATION_TIME
        self._otp_repository.insert_otp(otp, expiration_time)

        return otp

    def generate_refresh_token(self, user: User) -> Token:
        """
        Generates a refresh token for a specific user
        """
        return self._token_generator.generate_token(user.fs_uniquifier)

    def authorize_otp(self, otp: OTP) -> bool:
        # SECURITY: This method must not run concurrently, otherwise there could be TOCTOU errors,
        # resulting in an OTP being used twice.
        with self._otp_read_lock:
            try:
                otp_is_used = self._otp_repository.otp_is_used(otp)
                # When this method is called, that constitutes the OTP being "used".
                # Set it as used ASAP.
                self._otp_repository.set_used(otp)

                if otp_is_used:
                    return False

                if not self._otp_ttl_elapsed(otp):
                    return True

                return False
            except UnknownRecordError:
                return False

    def create_user(
        self, username: str, password: str, roles: Sequence[str], email: str = "dummy@dummy.com"
    ) -> User:
        return self._datastore.create_user(
            username=username,
            password=password,
            roles=roles,
            email=email,
        )

    def _otp_ttl_elapsed(self, otp: OTP) -> bool:
        return self._otp_repository.get_expiration(otp) < time.monotonic()

    def handle_successful_registration(self, username: str, password: str):
        self._reset_island_data()
        self._reset_repository_encryptor(username, password)

    def _reset_island_data(self):
        """
        Resets the island
        """
        self._island_event_queue.publish(IslandEventTopic.CLEAR_SIMULATION_DATA)
        self._island_event_queue.publish(IslandEventTopic.RESET_AGENT_CONFIGURATION)
        self._island_event_queue.publish(
            topic=IslandEventTopic.SET_ISLAND_MODE, mode=IslandMode.UNSET
        )

    def _reset_repository_encryptor(self, username: str, password: str):
        secret = _get_secret_from_credentials(username, password)
        self._repository_encryptor.reset_key()
        self._repository_encryptor.unlock(secret.encode())

    def handle_successful_login(self, username: str, password: str):
        self._unlock_repository_encryptor(username, password)

    def _unlock_repository_encryptor(self, username: str, password: str):
        secret = _get_secret_from_credentials(username, password)
        self._repository_encryptor.unlock(secret.encode())


def _get_secret_from_credentials(username: str, password: str) -> str:
    return f"{username}:{password}"
