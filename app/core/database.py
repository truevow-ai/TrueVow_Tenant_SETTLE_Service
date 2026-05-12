"""
Database Connection Module

Provides database connection utilities for the SETTLE Service.
Uses REST API directly via httpx to avoid Supabase client dependency issues.
"""

import logging
import asyncio
from typing import Optional, Any, Dict, List
from contextlib import asynccontextmanager
from functools import wraps
import json

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# Global client cache
_db_client = None


class SupabaseRESTResponse:
    """Mimics Supabase response object."""
    def __init__(self, data: Any = None, count: int = None):
        self.data = data
        self.count = count


class SupabaseRESTQuery:
    """Builder for Supabase REST queries."""
    
    def __init__(self, client: 'SupabaseRESTClient', table: str):
        self.client = client
        self.table_name = table
        self._filters: List[str] = []
        self._select_fields: str = "*"
        self._order_by: str = None
        self._order_desc: bool = False
        self._limit_val: int = None
        self._offset_val: int = None
        self._count_mode: str = None
    
    def select(self, *fields: str, count: str = None) -> 'SupabaseRESTQuery':
        """Select fields from table."""
        self._select_fields = ",".join(fields) if fields else "*"
        if count:
            self._count_mode = count
        return self
    
    def eq(self, column: str, value: Any) -> 'SupabaseRESTQuery':
        """Equal filter."""
        if isinstance(value, str):
            self._filters.append(f"{column}=eq.{value}")
        elif value is None:
            self._filters.append(f"{column}=is.null")
        else:
            self._filters.append(f"{column}=eq.{value}")
        return self
    
    def neq(self, column: str, value: Any) -> 'SupabaseRESTQuery':
        """Not equal filter."""
        if isinstance(value, str):
            self._filters.append(f"{column}=neq.{value}")
        else:
            self._filters.append(f"{column}=neq.{value}")
        return self
    
    def in_(self, column: str, values: List[Any]) -> 'SupabaseRESTQuery':
        """In filter."""
        vals = ",".join(f"{v}" if isinstance(v, str) else str(v) for v in values)
        self._filters.append(f"{column}=in.({vals})")
        return self
    
    def lt(self, column: str, value: Any) -> 'SupabaseRESTQuery':
        """Less than filter."""
        self._filters.append(f"{column}=lt.{value}")
        return self
    
    def lte(self, column: str, value: Any) -> 'SupabaseRESTQuery':
        """Less than or equal filter."""
        self._filters.append(f"{column}=lte.{value}")
        return self
    
    def gt(self, column: str, value: Any) -> 'SupabaseRESTQuery':
        """Greater than filter."""
        self._filters.append(f"{column}=gt.{value}")
        return self
    
    def gte(self, column: str, value: Any) -> 'SupabaseRESTQuery':
        """Greater than or equal filter."""
        self._filters.append(f"{column}=gte.{value}")
        return self
    
    def like(self, column: str, pattern: str) -> 'SupabaseRESTQuery':
        """Case-sensitive LIKE filter.

        URL-encodes all PostgREST-reserved chars including the SQL wildcards
        `%` and `_`. PostgREST URL-decodes the value once on receipt, restoring
        `%` and `_` as SQL LIKE wildcards on the server side. Symmetric with cs().
        """
        from urllib.parse import quote
        encoded = quote(pattern, safe='_')
        self._filters.append(f"{column}=like.{encoded}")
        return self
    
    def ilike(self, column: str, pattern: str) -> 'SupabaseRESTQuery':
        """Case-insensitive ILIKE filter.

        URL-encodes all PostgREST-reserved chars including the SQL wildcards
        `%` and `_`. PostgREST URL-decodes the value once on receipt, restoring
        `%` and `_` as SQL ILIKE wildcards on the server side. Symmetric with cs().
        """
        from urllib.parse import quote
        encoded = quote(pattern, safe='_')
        self._filters.append(f"{column}=ilike.{encoded}")
        return self

    def cs(self, column: str, values) -> 'SupabaseRESTQuery':
        """
        PostgREST array-contains operator: column contains ALL of these values.
        URL-encoded: column=cs.%7Bvalue1,value2%7D
        Pass a single string for single-value contains, or a list for multi-value.
        """
        if isinstance(values, str):
            values = [values]
        # PostgREST expects {val1,val2} with curly braces. Values containing
        # commas, spaces, or special chars need to be double-quoted inside.
        encoded_vals = []
        for v in values:
            v_str = str(v)
            # Quote if the value contains anything PostgREST might mis-parse
            if any(c in v_str for c in (',', ' ', '"', '\\', '{', '}')):
                v_str = '"' + v_str.replace('\\', '\\\\').replace('"', '\\"') + '"'
            encoded_vals.append(v_str)
        # URL-encode the curly braces (PostgREST requires them as part of value)
        from urllib.parse import quote
        payload = quote('{' + ','.join(encoded_vals) + '}')
        self._filters.append(f"{column}=cs.{payload}")
        return self

    def not_is(self, column: str, value: Any) -> 'SupabaseRESTQuery':
        """Not is filter (for null checks, etc)."""
        self._filters.append(f"{column}=not.is.{value}")
        return self
    
    @property
    def not_(self) -> 'SupabaseNOTBuilder':
        """Returns NOT query builder for negation filters."""
        return SupabaseNOTBuilder(self)
    
    def order(self, column: str, desc: bool = False) -> 'SupabaseRESTQuery':
        """Order results."""
        self._order_by = column
        self._order_desc = desc
        return self
    
    def limit(self, count: int) -> 'SupabaseRESTQuery':
        """Limit results."""
        self._limit_val = count
        return self
    
    def offset(self, count: int) -> 'SupabaseRESTQuery':
        """Offset results."""
        self._offset_val = count
        return self
    
    def _build_url(self) -> str:
        """Build the full URL for the query."""
        url = f"{self.client.base_url}/rest/v1/{self.table_name}"
        params = []
        
        if self._select_fields != "*":
            params.append(f"select={self._select_fields}")
        
        params.extend(self._filters)
        
        if self._order_by:
            direction = "desc" if self._order_desc else "asc"
            params.append(f"order={self._order_by}.{direction}")
        
        if self._limit_val:
            params.append(f"limit={self._limit_val}")
        
        if self._offset_val:
            params.append(f"offset={self._offset_val}")
        
        if params:
            url += "?" + "&".join(params)
        
        return url
    
    def execute(self) -> SupabaseRESTResponse:
        """Execute the query synchronously."""
        url = self._build_url()
        headers = self.client.headers.copy()
        
        if self._count_mode:
            headers["Prefer"] = f"count={self._count_mode}"
        
        try:
            response = httpx.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            data = response.json()
            
            # Get count from content-range header
            count = None
            if self._count_mode:
                content_range = response.headers.get("content-range", "")
                if "/" in content_range:
                    count_str = content_range.split("/")[-1]
                    if count_str != "*":
                        count = int(count_str)
            
            return SupabaseRESTResponse(data=data, count=count)
            
        except httpx.HTTPError as e:
            logger.error(f"REST query failed: {e}")
            return SupabaseRESTResponse(data=None, count=None)


class SupabaseNOTBuilder:
    """Builder for NOT filters in Supabase REST API."""
    
    def __init__(self, query: SupabaseRESTQuery):
        self._query = query
    
    def is_(self, column: str, value: Any) -> SupabaseRESTQuery:
        """NOT IS filter (e.g., for null checks)."""
        self._query._filters.append(f"{column}=not.is.{value}")
        return self._query
    
    def eq(self, column: str, value: Any) -> SupabaseRESTQuery:
        """NOT EQUAL filter."""
        self._query._filters.append(f"{column}=not.eq.{value}")
        return self._query
    
    def like(self, column: str, pattern: str) -> SupabaseRESTQuery:
        """NOT LIKE filter."""
        self._query._filters.append(f"{column}=not.like.{pattern}")
        return self._query
    
    def ilike(self, column: str, pattern: str) -> SupabaseRESTQuery:
        """NOT ILIKE filter."""
        self._query._filters.append(f"{column}=not.ilike.{pattern}")
        return self._query
    
    def in_(self, column: str, values: List[Any]) -> SupabaseRESTQuery:
        """NOT IN filter."""
        vals = ",".join(str(v) for v in values)
        self._query._filters.append(f"{column}=not.in.({vals})")
        return self._query


class SupabaseRESTClient:
    """
    REST API client for Supabase that mimics the Python client interface.
    Uses httpx directly to avoid dependency compatibility issues.
    """
    
    def __init__(self, base_url: str, service_key: str):
        self.base_url = base_url.rstrip("/")
        self.service_key = service_key
        self.headers = {
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
            "Content-Type": "application/json",
        }
    
    def table(self, name: str) -> SupabaseRESTQuery:
        """Get a table query builder."""
        return SupabaseTable(self, name)


class SupabaseTable:
    """Table operations for Supabase REST API."""
    
    def __init__(self, client: SupabaseRESTClient, table_name: str):
        self.client = client
        self.table_name = table_name
    
    def select(self, *fields: str, count: str = None) -> SupabaseRESTQuery:
        """Select from table."""
        query = SupabaseRESTQuery(self.client, self.table_name)
        return query.select(*fields, count=count)
    
    def insert(self, data: Dict) -> SupabaseRESTQuery:
        """Insert into table."""
        return SupabaseInsertQuery(self.client, self.table_name, data)
    
    def update(self, data: Dict) -> SupabaseRESTQuery:
        """Update table."""
        return SupabaseUpdateQuery(self.client, self.table_name, data)
    
    def delete(self) -> SupabaseRESTQuery:
        """Delete from table."""
        return SupabaseDeleteQuery(self.client, self.table_name)


class SupabaseInsertQuery:
    """Insert query builder."""
    
    def __init__(self, client: SupabaseRESTClient, table: str, data: Dict):
        self.client = client
        self.table_name = table
        self.data = data
    
    def execute(self) -> SupabaseRESTResponse:
        """Execute insert."""
        url = f"{self.client.base_url}/rest/v1/{self.table_name}"
        headers = self.client.headers.copy()
        headers["Prefer"] = "return=representation"
        
        try:
            response = httpx.post(
                url,
                headers=headers,
                json=self.data,
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            return SupabaseRESTResponse(data=data)
            
        except httpx.HTTPError as e:
            logger.error(f"Insert failed: {e}")
            return SupabaseRESTResponse(data=None)


class SupabaseUpdateQuery:
    """Update query builder."""
    
    def __init__(self, client: SupabaseRESTClient, table: str, data: Dict):
        self.client = client
        self.table_name = table
        self.data = data
        self._filters: List[str] = []
    
    def eq(self, column: str, value: Any) -> 'SupabaseUpdateQuery':
        """Equal filter."""
        if isinstance(value, str):
            self._filters.append(f"{column}=eq.{value}")
        else:
            self._filters.append(f"{column}=eq.{value}")
        return self
    
    def execute(self) -> SupabaseRESTResponse:
        """Execute update."""
        url = f"{self.client.base_url}/rest/v1/{self.table_name}"
        if self._filters:
            url += "?" + "&".join(self._filters)
        
        headers = self.client.headers.copy()
        headers["Prefer"] = "return=representation"
        
        try:
            response = httpx.patch(
                url,
                headers=headers,
                json=self.data,
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            return SupabaseRESTResponse(data=data)
            
        except httpx.HTTPError as e:
            logger.error(f"Update failed: {e}")
            return SupabaseRESTResponse(data=None)


class SupabaseDeleteQuery:
    """Delete query builder."""
    
    def __init__(self, client: SupabaseRESTClient, table: str):
        self.client = client
        self.table_name = table
        self._filters: List[str] = []
    
    def eq(self, column: str, value: Any) -> 'SupabaseDeleteQuery':
        """Equal filter."""
        if isinstance(value, str):
            self._filters.append(f"{column}=eq.{value}")
        else:
            self._filters.append(f"{column}=eq.{value}")
        return self
    
    def execute(self) -> SupabaseRESTResponse:
        """Execute delete."""
        url = f"{self.client.base_url}/rest/v1/{self.table_name}"
        if self._filters:
            url += "?" + "&".join(self._filters)
        
        try:
            response = httpx.delete(
                url,
                headers=self.client.headers,
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json() if response.content else None
            return SupabaseRESTResponse(data=data)
            
        except httpx.HTTPError as e:
            logger.error(f"Delete failed: {e}")
            return SupabaseRESTResponse(data=None)


def with_retry(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    Decorator for retry logic on database operations.
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay after each retry
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"Database operation failed (attempt {attempt + 1}/{max_retries + 1}): {str(e)}. "
                            f"Retrying in {current_delay}s..."
                        )
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"Database operation failed after {max_retries + 1} attempts: {str(e)}",
                            exc_info=True
                        )
            
            raise last_exception
        return wrapper
    return decorator


async def get_db() -> Optional[Any]:
    """
    Get database connection with retry logic.
    
    Uses REST API directly instead of Supabase client to avoid dependency issues.
    
    Returns:
        SupabaseRESTClient or None in mock mode
    """
    global _db_client
    
    if settings.use_mock_data:
        logger.debug("Mock mode: returning None for database connection")
        return None
    
    # Return cached client if available
    if _db_client is not None:
        return _db_client
    
    try:
        # Get HTTP URL for REST API.
        # Use the canonical supabase_url property which honors the SETTLE_DATABASE_*
        # convention (chains SETTLE_DATABASE_URL -> SETTLE_SUPABASE_URL -> ...).
        # Symmetric with the supabase_service_key property usage below.
        supabase_url = settings.supabase_url

        # Defensive: SupabaseRESTClient needs the HTTPS REST URL, not a
        # postgres:// connection string. If supabase_url resolves to a connection
        # string (e.g. only DIRECT/POOLER URLs are configured), reject it.
        if supabase_url and not supabase_url.startswith("http"):
            logger.warning(
                f"get_db(): supabase_url returned non-HTTPS value "
                f"(scheme={supabase_url.split(':', 1)[0]}). "
                f"SupabaseRESTClient requires the HTTPS REST URL. "
                f"Check SETTLE_DATABASE_URL in .env.local \u2014 it should be "
                f"https://<project-ref>.supabase.co, not a postgres:// connection string."
            )
            supabase_url = None

        # Get service role key for admin access
        supabase_key = settings.supabase_service_key
        
        if not supabase_url or not supabase_key:
            logger.warning("Supabase credentials not configured - returning None")
            return None
        
        # Ensure URL is HTTP URL, not database connection string
        if supabase_url.startswith('postgresql://') or supabase_url.startswith('postgres://'):
            import re
            match = re.search(r'postgres\.([a-z]+)\.', supabase_url)
            if match:
                project_id = match.group(1)
                supabase_url = f"https://{project_id}.supabase.co"
            else:
                logger.warning("Could not extract project ID from database URL")
                return None
        
        # Create REST client instead of Supabase client
        _db_client = SupabaseRESTClient(supabase_url, supabase_key)
        logger.info(f"Database REST connection established: {supabase_url}")
        return _db_client
        
    except Exception as e:
        logger.error(f"Failed to create database connection: {str(e)}", exc_info=True)
        return None


async def get_db_with_retry(retries: int = 3) -> Optional[Any]:
    """
    Get database connection with explicit retry.
    
    Args:
        retries: Number of retry attempts
        
    Returns:
        Supabase client or None
    """
    # In mock mode, skip retries entirely
    if settings.USE_MOCK_DATA:
        return await get_db()
    
    for attempt in range(retries):
        db = await get_db()
        if db is not None:
            return db
        
        if attempt < retries - 1:
            logger.info(f"Retrying database connection (attempt {attempt + 2}/{retries})")
            await asyncio.sleep(1 * (attempt + 1))
    
    return None


@asynccontextmanager
async def get_db_session():
    """
    Get database session context manager.
    
    Usage:
        async with get_db_session() as db:
            # Use db connection
            pass
    """
    db = await get_db()
    try:
        yield db
    finally:
        # Supabase client doesn't need explicit cleanup
        pass


async def health_check() -> dict:
    """
    Check database health.
    
    Returns:
        Dict with health status
    """
    try:
        db = await get_db_with_retry(retries=1)
        
        if db is None:
            return {
                "status": "degraded",
                "message": "Database not configured or mock mode"
            }
        
        # Simple query to verify connection
        result = db.table("settle_contributions").select("id").limit(1).execute()
        
        return {
            "status": "healthy",
            "message": "Database connection successful"
        }
        
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "message": str(e)
        }


def reset_client():
    """
    Reset the cached database client.
    Used for testing or reconnection scenarios.
    """
    global _db_client
    _db_client = None
    logger.info("Database client cache reset")
