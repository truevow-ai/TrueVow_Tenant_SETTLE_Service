"""
DOCKET-Service Database Client
Reuses the same Supabase REST client pattern as SETTLE-Service.
"""

import logging
from typing import Optional, Any, Dict, List
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_db_client = None


class SupabaseRESTClient:
    """Supabase REST API client using httpx."""

    def __init__(self, url: str, key: str):
        self.url = url.rstrip("/")
        self.key = key
        self.headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }
        self.client = httpx.AsyncClient(base_url=url, headers=self.headers, timeout=30)

    def table(self, table_name: str) -> "SupabaseTable":
        return SupabaseTable(self, table_name)

    async def close(self):
        await self.client.aclose()


class SupabaseTable:
    """Represents a Supabase table query."""

    def __init__(self, client: SupabaseRESTClient, table_name: str):
        self.client = client
        self.table_name = table_name
        self._select_columns = "*"
        self._filters: List[Dict[str, Any]] = []
        self._order_by: Optional[str] = None
        self._order_desc = False
        self._limit_val: Optional[int] = None
        self._offset_val: Optional[int] = None
        self._count_mode: Optional[str] = None

    def select(self, columns: str = "*", count: Optional[str] = None) -> "SupabaseTable":
        self._select_columns = columns
        self._count_mode = count
        return self

    def eq(self, column: str, value: Any) -> "SupabaseTable":
        self._filters.append({"op": "eq", "column": column, "value": value})
        return self

    def neq(self, column: str, value: Any) -> "SupabaseTable":
        self._filters.append({"op": "neq", "column": column, "value": value})
        return self

    def in_(self, column: str, values: List[Any]) -> "SupabaseTable":
        self._filters.append({"op": "in", "column": column, "value": values})
        return self

    def gt(self, column: str, value: Any) -> "SupabaseTable":
        self._filters.append({"op": "gt", "column": column, "value": value})
        return self

    def gte(self, column: str, value: Any) -> "SupabaseTable":
        self._filters.append({"op": "gte", "column": column, "value": value})
        return self

    def lt(self, column: str, value: Any) -> "SupabaseTable":
        self._filters.append({"op": "lt", "column": column, "value": value})
        return self

    def lte(self, column: str, value: Any) -> "SupabaseTable":
        self._filters.append({"op": "lte", "column": column, "value": value})
        return self

    def like(self, column: str, pattern: str) -> "SupabaseTable":
        self._filters.append({"op": "like", "column": column, "value": pattern})
        return self

    def ilike(self, column: str, pattern: str) -> "SupabaseTable":
        self._filters.append({"op": "ilike", "column": column, "value": pattern})
        return self

    def is_(self, column: str, value: Any) -> "SupabaseTable":
        self._filters.append({"op": "is", "column": column, "value": value})
        return self

    def order(self, column: str, desc: bool = False) -> "SupabaseTable":
        self._order_by = column
        self._order_desc = desc
        return self

    def limit(self, n: int) -> "SupabaseTable":
        self._limit_val = n
        return self

    def offset(self, n: int) -> "SupabaseTable":
        self._offset_val = n
        return self

    async def execute(self):
        """Execute the query and return results."""
        params = {}
        headers = dict(self.client.headers)

        # Build select params
        select_param = self._select_columns
        if self._count_mode:
            select_param += f";count={self._count_mode}"
        params["select"] = select_param

        # Apply filters
        for f in self._filters:
            if f["op"] == "eq":
                params[f[f"column"]] = f"eq.{f['value']}" if not isinstance(f["value"], str) else f"eq.{f['value']}"
            elif f["op"] == "neq":
                params[f[f"column"]] = f"neq.{f['value']}"
            elif f["op"] == "gt":
                params[f[f"column"]] = f"gt.{f['value']}"
            elif f["op"] == "gte":
                params[f[f"column"]] = f"gte.{f['value']}"
            elif f["op"] == "lt":
                params[f[f"column"]] = f"lt.{f['value']}"
            elif f["op"] == "lte":
                params[f[f"column"]] = f"lte.{f['value']}"
            elif f["op"] == "like":
                params[f[f"column"]] = f"like.{f['value']}"
            elif f["op"] == "ilike":
                params[f[f"column"]] = f"ilike.{f['value']}"
            elif f["op"] == "is":
                params[f[f"column"]] = f"is.{f['value']}"
            elif f["op"] == "in":
                vals = ",".join(str(v) for v in f["value"])
                params[f[f"column"]] = f"in.({vals})"

        # Order
        if self._order_by:
            params["order"] = f"{self._order_by}{'.desc' if self._order_desc else ''}"

        # Limit/Offset
        if self._limit_val is not None:
            headers["Range-Unit"] = "items"
            offset = self._offset_val or 0
            headers["Range"] = f"{offset}-{offset + self._limit_val - 1}"

        url = f"{self.client.url}/rest/v1/{self.table_name}"

        try:
            response = await self.client.client.get(url, params=params, headers=headers)
            response.raise_for_status()

            data = response.json()
            count = None
            if self._count_mode and "content-range" in response.headers:
                count_range = response.headers["content-range"]
                count = int(count_range.split("/")[-1]) if count_range != "*/0" else 0

            return SupabaseResponse(data=data, count=count)
        except Exception as e:
            logger.error(f"DOCKET DB query failed: {e}")
            return SupabaseResponse(data=[], count=None)

    async def insert(self, data: Dict[str, Any]) -> "SupabaseInsertQuery":
        return SupabaseInsertQuery(self.client, self.table_name, data)

    async def update(self, data: Dict[str, Any]) -> "SupabaseUpdateQuery":
        return SupabaseUpdateQuery(self.client, self.table_name, data)


class SupabaseInsertQuery:
    def __init__(self, client: SupabaseRESTClient, table_name: str, data: Dict[str, Any]):
        self.client = client
        self.table_name = table_name
        self.data = data

    async def execute(self):
        url = f"{self.client.url}/rest/v1/{self.table_name}"
        try:
            response = await self.client.client.post(url, json=self.data)
            response.raise_for_status()
            return SupabaseResponse(data=response.json(), count=None)
        except Exception as e:
            logger.error(f"DOCKET DB insert failed: {e}")
            return SupabaseResponse(data=[], count=None)


class SupabaseUpdateQuery:
    def __init__(self, client: SupabaseRESTClient, table_name: str, data: Dict[str, Any]):
        self.client = client
        self.table_name = table_name
        self.data = data
        self._filters: List[Dict[str, Any]] = []

    def eq(self, column: str, value: Any) -> "SupabaseUpdateQuery":
        self._filters.append({"column": column, "value": value})
        return self

    async def execute(self):
        params = {}
        for f in self._filters:
            params[f[f"column"]] = f"eq.{f['value']}"

        url = f"{self.client.url}/rest/v1/{self.table_name}"
        try:
            response = await self.client.client.patch(url, json=self.data, params=params)
            response.raise_for_status()
            return SupabaseResponse(data=response.json(), count=None)
        except Exception as e:
            logger.error(f"DOCKET DB update failed: {e}")
            return SupabaseResponse(data=[], count=None)


class SupabaseResponse:
    def __init__(self, data: Any, count: Optional[int]):
        self.data = data
        self.count = count


async def get_db() -> SupabaseRESTClient:
    """Get database client singleton."""
    global _db_client
    if _db_client is None:
        _db_client = SupabaseRESTClient(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    return _db_client
