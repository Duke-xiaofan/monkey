from ipaddress import IPv4Interface
from typing import Optional, Sequence

from pydantic import Field, validator

from common import OperatingSystem
from common.base_models import MutableInfectionMonkeyBaseModel
from common.transforms import make_immutable_sequence
from common.types import HardwareID

from . import MachineID


class Machine(MutableInfectionMonkeyBaseModel):
    """Represents machines, VMs, or other network nodes discovered by Infection Monkey"""

    id: MachineID = Field(..., allow_mutation=False)
    """Uniquely identifies the machine within the island"""

    hardware_id: Optional[HardwareID]
    """An identifier generated by the agent that uniquely identifies a machine"""

    island: bool = Field(default=False, allow_mutation=False)
    """Whether or not the machine is an island (C&C server)"""

    network_interfaces: Sequence[IPv4Interface] = tuple()
    """The machine's networking interfaces"""

    operating_system: Optional[OperatingSystem]
    """The operating system the machine is running"""

    operating_system_version: str = ""
    """The specific version of the operating system the machine is running"""

    hostname: str = ""
    """The hostname of the machine"""

    _make_immutable_sequence = validator("network_interfaces", pre=True, allow_reuse=True)(
        make_immutable_sequence
    )

    def __hash__(self):
        return self.id
