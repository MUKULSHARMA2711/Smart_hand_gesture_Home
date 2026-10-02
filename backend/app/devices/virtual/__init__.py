"""In-memory device implementations used until real hardware is available."""

from app.devices.virtual.ac import VirtualAC
from app.devices.virtual.base import VirtualDevice
from app.devices.virtual.door import VirtualDoorLock
from app.devices.virtual.fan import VirtualFan
from app.devices.virtual.light import VirtualLight

__all__ = ["VirtualAC", "VirtualDevice", "VirtualDoorLock", "VirtualFan", "VirtualLight"]
