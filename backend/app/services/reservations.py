import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class RevenueDataUnavailable(RuntimeError):
    """
    Raised when revenue cannot be read from the database.

    Callers must surface this as an error. Returning a plausible-looking
    number in its place is what hid the broken connection pool for so long.
    """

async def calculate_monthly_revenue(property_id: str, month: int, year: int, db_session=None) -> Decimal:
    """
    Calculates revenue for a specific month.
    """

    start_date = datetime(year, month, 1)
    if month < 12:
        end_date = datetime(year, month + 1, 1)
    else:
        end_date = datetime(year + 1, 1, 1)
        
    print(f"DEBUG: Querying revenue for {property_id} from {start_date} to {end_date}")

    # SQL Simulation (This would be executed against the actual DB)
    query = """
        SELECT SUM(total_amount) as total
        FROM reservations
        WHERE property_id = $1
        AND tenant_id = $2
        AND check_in_date >= $3
        AND check_in_date < $4
    """
    
    # In production this query executes against a database session.
    # result = await db.fetch_val(query, property_id, tenant_id, start_date, end_date)
    # return result or Decimal('0')
    
    return Decimal('0') # Placeholder for now until DB connection is finalized

async def calculate_total_revenue(property_id: str, tenant_id: str) -> Dict[str, Any]:
    """
    Aggregates revenue from database.
    """
    from app.core.database_pool import db_pool
    from sqlalchemy import text

    query = text("""
        SELECT
            COALESCE(SUM(total_amount), 0) as total_revenue,
            COUNT(*) as reservation_count
        FROM reservations
        WHERE property_id = :property_id AND tenant_id = :tenant_id
    """)

    try:
        await db_pool.initialize()
        async with db_pool.get_session() as session:
            result = await session.execute(query, {
                "property_id": property_id,
                "tenant_id": tenant_id
            })
            row = result.fetchone()
    except Exception as e:
        logger.error(f"Database error for {property_id} (tenant: {tenant_id}): {e}")
        raise RevenueDataUnavailable(
            f"Could not read revenue for {property_id}"
        ) from e

    # An aggregate without GROUP BY always returns exactly one row, so a
    # property with no reservations reports 0.00 rather than falling through
    # to a branch that could invent a figure.
    total_revenue = Decimal(str(row.total_revenue))

    return {
        "property_id": property_id,
        "tenant_id": tenant_id,
        "total": str(total_revenue),
        "currency": "USD",
        "count": row.reservation_count
    }
