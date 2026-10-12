import json
import logging
import redis.asyncio as redis
from typing import Dict, Any
import os

logger = logging.getLogger(__name__)

# Initialize Redis client (typically configured centrally).
redis_client = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))

CACHE_TTL_SECONDS = 300


def build_cache_key(property_id: str, tenant_id: str) -> str:
    """
    Builds the revenue cache key.

    The tenant is part of the key because property ids are only unique within a
    tenant: properties.id is PRIMARY KEY (id, tenant_id), so two tenants can
    both own a 'prop-001'. Keying on property_id alone lets one tenant's totals
    be served to another.
    """
    return f"revenue:{tenant_id}:{property_id}"


async def get_revenue_summary(property_id: str, tenant_id: str) -> Dict[str, Any]:
    """
    Fetches revenue summary, utilizing caching to improve performance.
    """
    cache_key = build_cache_key(property_id, tenant_id)

    # Try to get from cache
    try:
        cached = await redis_client.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception as e:
        # A cache outage must not take the dashboard down; fall through and
        # calculate from the database instead.
        logger.warning(f"Cache read failed for {cache_key}: {e}")

    # Revenue calculation is delegated to the reservation service.
    from app.services.reservations import calculate_total_revenue

    # Calculate revenue
    result = await calculate_total_revenue(property_id, tenant_id)

    # Cache the result for 5 minutes
    try:
        await redis_client.setex(cache_key, CACHE_TTL_SECONDS, json.dumps(result))
    except Exception as e:
        logger.warning(f"Cache write failed for {cache_key}: {e}")

    return result
