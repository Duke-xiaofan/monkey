import json
from http import HTTPStatus

from flask import make_response, request

from common.agent_configuration.agent_configuration import (
    AgentConfiguration as AgentConfigurationObject,
)
from monkey_island.cc.resources.AbstractResource import AbstractResource
from monkey_island.cc.resources.request_authentication import jwt_required
from monkey_island.cc.services import IAgentConfigurationService, PluginConfigurationValidationError


class AgentConfiguration(AbstractResource):
    urls = ["/api/agent-configuration"]

    def __init__(self, agent_configuration_service: IAgentConfigurationService):
        self._agent_configuration_service = agent_configuration_service

    # Used by the agent. Can't secure
    def get(self):
        configuration = self._agent_configuration_service.get_configuration()
        configuration_dict = configuration.dict(simplify=True)
        return make_response(configuration_dict, 200)

    @jwt_required
    def put(self):
        try:
            configuration_object = AgentConfigurationObject(**request.json)
            self._agent_configuration_service.update_configuration(configuration_object)
            return make_response({}, HTTPStatus.NO_CONTENT)
        except (
            ValueError,
            TypeError,
            json.JSONDecodeError,
            PluginConfigurationValidationError,
        ) as err:

            return make_response(
                {"error": f"Invalid configuration supplied: {err}"},
                HTTPStatus.BAD_REQUEST,
            )
