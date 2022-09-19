import logging

import requests

from common.common_consts.timeouts import MEDIUM_REQUEST_TIMEOUT

from . import IIslandAPIClient, IslandAPIConnectionError, IslandAPIError, IslandAPITimeoutError

logger = logging.getLogger(__name__)


class HTTPIslandAPIClient(IIslandAPIClient):
    """
    A client for the Island's HTTP API
    """

    def __init__(self, island_server: str):
        try:
            requests.get(  # noqa: DUO123
                f"https://{island_server}/api?action=is-up",
                verify=False,
                timeout=MEDIUM_REQUEST_TIMEOUT,
            )
            self._island_server = island_server
        except requests.exceptions.ConnectionError as err:
            raise IslandAPIConnectionError(err)
        except TimeoutError as err:
            raise IslandAPITimeoutError(err)
        except Exception as err:
            raise IslandAPIError(err)

        # TODO: set server address as object property when init is called in find_server and pass
        #       object around? won't need to pass island server and create object in every function
        def send_log(self, data: str):
            requests.post(  # noqa: DUO123
                "https://%s/api/log" % (self._island_server,),
                json=data,
                verify=False,
                timeout=MEDIUM_REQUEST_TIMEOUT,
            )
