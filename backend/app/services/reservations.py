from datetime import datetime
from decimal import Decimal
from typing import Dict, Any

from sqlalchemy import text
from app.core.database_pool import db_pool

async def calculate_monthly_revenue(property_id: str, tenant_id: str, month: int, year: int) -> Decimal:
    """
    Calculates revenue for a specific month, bucketed in the PROPERTY's local time zone.
    """
    start_date = datetime(year, month, 1)
    end_date = datetime(year + 1, 1, 1) if month == 12 else datetime(year, month + 1, 1)
        
    print(f"DEBUG: Querying timezone-aware revenue for {property_id} from {start_date} to {end_date}")

    query = text("""
        SELECT COALESCE(SUM(r.total_amount), 0) AS total
        FROM reservations r
        JOIN properties p
          ON p.id = r.property_id AND p.tenant_id = r.tenant_id
        WHERE r.property_id = :property_id
          AND r.tenant_id = :tenant_id
          AND (r.check_in_date AT TIME ZONE p.timezone) >= :start_date
          AND (r.check_in_date AT TIME ZONE p.timezone) <  :end_date
    """)

    await db_pool.initialize()
    async with db_pool.get_session() as session:
        result = await session.execute(query, {
            "property_id": property_id,
            "tenant_id": tenant_id,
            "start_date": start_date,
            "end_date": end_date,
        })
        return Decimal(str(result.scalar_one()))

async def calculate_total_revenue(property_id: str, tenant_id: str) -> Dict[str, Any]:
    """
    Aggregates revenue from database.
    """
    query = text("""
        SELECT 
            property_id,
            COALESCE(SUM(total_amount), 0) as total_revenue,
            COUNT(*) as reservation_count
        FROM reservations 
        WHERE property_id = :property_id AND tenant_id = :tenant_id
        GROUP BY property_id
    """)
    
    await db_pool.initialize()
    async with db_pool.get_session() as session:
        result = await session.execute(query, {
            "property_id": property_id, 
            "tenant_id": tenant_id
        })
        row = result.fetchone()
        
        if row:
            return {
                "property_id": property_id,
                "tenant_id": tenant_id,
                "total": str(Decimal(str(row.total_revenue))),
                "currency": "USD", 
                "count": row.reservation_count
            }
        
        # Return zeros if no rows found instead of failing
        return {
            "property_id": property_id,
            "tenant_id": tenant_id,
            "total": "0.00",
            "currency": "USD",
            "count": 0
        }
