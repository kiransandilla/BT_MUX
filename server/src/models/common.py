"""Common Pydantic types and utilities for BT-Mux models."""
from typing import Annotated, Any
from pydantic import BeforeValidator


def _validate_object_id(v: Any) -> Any:
    """Convert BSON ObjectId or any non-None value to string."""
    if v is None:
        return None
    return str(v)


PyObjectId = Annotated[str, BeforeValidator(_validate_object_id)]
