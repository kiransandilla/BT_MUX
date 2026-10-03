"""In-memory Mock MongoDB database for unit and integration testing without daemon."""
from typing import Any, Dict, List, Optional
from bson import ObjectId


class MockCursor:
    """Mock MongoDB query cursor."""

    def __init__(self, docs: List[Dict[str, Any]]):
        self._docs = docs

    def sort(self, key: str, direction: int = 1) -> "MockCursor":
        reverse = (direction == -1)
        self._docs.sort(key=lambda d: d.get(key, 0) or 0, reverse=reverse)
        return self

    def limit(self, count: int) -> "MockCursor":
        self._docs = self._docs[:count]
        return self

    async def to_list(self, length: Optional[int] = None) -> List[Dict[str, Any]]:
        if length is not None:
            return self._docs[:length]
        return self._docs


class MockCollection:
    """Mock MongoDB collection storing documents in memory."""

    def __init__(self, name: str):
        self.name = name
        self.docs: List[Dict[str, Any]] = []

    def _matches(self, doc: Dict[str, Any], query: Dict[str, Any]) -> bool:
        if not query:
            return True
        if "$or" in query:
            return any(self._matches(doc, q) for q in query["$or"])
        for k, v in query.items():
            if k == "_id":
                if str(doc.get("_id")) != str(v):
                    return False
            elif doc.get(k) != v:
                return False
        return True

    async def insert_one(self, doc: Dict[str, Any]) -> Any:
        d = dict(doc)
        if "_id" not in d:
            d["_id"] = ObjectId()
        self.docs.append(d)

        class Result:
            inserted_id = d["_id"]

        return Result()

    async def find_one(
        self,
        query: Optional[Dict[str, Any]] = None,
        sort: Optional[List[tuple]] = None,
    ) -> Optional[Dict[str, Any]]:
        matches = [d for d in self.docs if self._matches(d, query or {})]
        if not matches:
            return None
        if sort:
            key, direction = sort[0]
            reverse = (direction == -1)
            matches.sort(key=lambda d: d.get(key, 0) or 0, reverse=reverse)
        return dict(matches[0])

    def find(self, query: Optional[Dict[str, Any]] = None) -> MockCursor:
        matches = [dict(d) for d in self.docs if self._matches(d, query or {})]
        return MockCursor(matches)

    async def update_one(self, query: Dict[str, Any], update: Dict[str, Any]) -> None:
        for d in self.docs:
            if self._matches(d, query):
                if "$set" in update:
                    d.update(update["$set"])
                break

    async def delete_one(self, query: Dict[str, Any]) -> None:
        for i, d in enumerate(self.docs):
            if self._matches(d, query):
                del self.docs[i]
                break

    async def delete_many(self, query: Dict[str, Any]) -> None:
        self.docs = [d for d in self.docs if not self._matches(d, query)]

    async def create_index(self, *args, **kwargs) -> str:
        return "mock_index"


class MockDatabase:
    """Mock MongoDB database instance for dependency injection."""

    def __init__(self, name: str = "bt_mux_test"):
        self.name = name
        self.collections: Dict[str, MockCollection] = {}

    def __getitem__(self, name: str) -> MockCollection:
        if name not in self.collections:
            self.collections[name] = MockCollection(name)
        return self.collections[name]

    async def command(self, cmd: str) -> Dict[str, Any]:
        if cmd == "ping":
            return {"ok": 1.0}
        return {}
