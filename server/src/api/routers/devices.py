"""FastAPI router for BLE Device registry."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from ...db.motor import get_db
from ...models.device import Device
from ...schemas.device import DeviceCreate, DeviceResponse
from ..utils import doc_to_response, id_query

router = APIRouter(prefix="/api/devices", tags=["Devices"])


@router.post("", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED)
async def register_device(
    payload: DeviceCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> DeviceResponse:
    """Register a new BLE peripheral or simulated node."""
    # Check if device with same MAC already exists
    existing = await db["devices"].find_one({"mac_address": payload.mac_address})
    if existing:
        return DeviceResponse(**doc_to_response(existing))

    device = Device(
        device_name=payload.device_name,
        device_type=payload.device_type,
        mac_address=payload.mac_address,
    )
    doc = device.model_dump(by_alias=True, exclude_none=True)
    result = await db["devices"].insert_one(doc)
    doc["id"] = str(result.inserted_id)
    return DeviceResponse(**doc)


@router.get("", response_model=List[DeviceResponse])
async def list_devices(
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> List[DeviceResponse]:
    """Retrieve all registered BLE peripherals / nodes."""
    cursor = db["devices"].find()
    devices = await cursor.to_list(length=200)
    return [DeviceResponse(**doc_to_response(d)) for d in devices]


@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(
    device_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> DeviceResponse:
    """Retrieve device details by ID."""
    doc = await db["devices"].find_one(id_query(device_id))
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device with ID '{device_id}' not found",
        )
    return DeviceResponse(**doc_to_response(doc))


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device(
    device_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> None:
    """Delete a registered device."""
    query = id_query(device_id)
    doc = await db["devices"].find_one(query)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device with ID '{device_id}' not found",
        )
    await db["devices"].delete_one(query)
