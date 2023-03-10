import flask_restful

from common import DIContainer

from ..authentication_facade import AuthenticationFacade
from .agent_otp import AgentOTP
from .login import Login
from .logout import Logout
from .otp_login import OTPLogin
from .register import Register
from .registration_status import RegistrationStatus


def register_resources(api: flask_restful.Api, container: DIContainer):
    authentication_facade = container.resolve(AuthenticationFacade)

    api.add_resource(Register, *Register.urls, resource_class_args=(authentication_facade,))
    api.add_resource(
        RegistrationStatus, *RegistrationStatus.urls, resource_class_args=(authentication_facade,)
    )
    api.add_resource(Login, *Login.urls, resource_class_args=(authentication_facade,))
    api.add_resource(Logout, *Logout.urls, resource_class_args=(authentication_facade,))
    api.add_resource(AgentOTP, *AgentOTP.urls)
    api.add_resource(OTPLogin, *OTPLogin.urls)
