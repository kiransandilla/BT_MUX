"""API routing and database utility helpers."""
from typing import Any, Dict
from bson import ObjectId


def id_query(id_str: str) -> Dict[str, Any]:
    """Construct MongoDB query filter matching either BSON ObjectId or string representation."""
    if ObjectId.is_valid(id_str):
        return {"$or": [{"_id": ObjectId(id_str)}, {"_id": id_str}]}
    return {"_id": id_str}


def doc_to_response(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Transform a MongoDB document converting '_id' to 'id' string."""
    if not doc:
        return {}
    res = dict(doc)
    if "_id" in res:
        res["id"] = str(res.pop("_id"))
    return res
