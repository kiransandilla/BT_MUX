"""Device API request and response schemas."""
from pydantic import BaseModel, ConfigDict, Field


class DeviceCreate(BaseModel):
    """Payload to register a new BLE peripheral or simulated node."""
    device_name: str = Field(..., description="Name or advertisement string of device")
    device_type: str = Field(..., description="Device classification (e.g. sensor, file_peer)")
    mac_address: str = Field(..., description="Bluetooth MAC or Device Address")


class DeviceResponse(BaseModel):
    """Complete device document representation returned by API."""
    id: str
    device_name: str
    device_type: str
    mac_address: str

    model_config = ConfigDict(from_attributes=True)
