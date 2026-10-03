"""Device data model for physical BLE peripherals.

Authoritative source: BT-Mux_Agent_Instructions.md Section 4.
"""
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

from .common import PyObjectId


class Device(BaseModel):
    """Device document representing one physical BLE peripheral.
    
    Fields:
    - id / _id: MongoDB document identifier.
    - device_name: Human-readable name or broadcast advertising name.
    - device_type: Peripheral type/category (e.g., 'sensor', 'file_peer', 'simulated_node').
    - mac_address: Physical MAC or Bluetooth Device Address (e.g., 'AA:BB:CC:DD:EE:FF').
    """
    id: Optional[PyObjectId] = Field(None, alias="_id")
    device_name: str
    device_type: str
    mac_address: str

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )
