from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any
from app.services.cache import get_revenue_summary
from app.services.reservations import RevenueDataUnavailable
from app.core.auth import authenticate_request as get_current_user

router = APIRouter()

@router.get("/dashboard/summary")
async def get_dashboard_summary(
    property_id: str,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    
    tenant_id = getattr(current_user, "tenant_id", "default_tenant") or "default_tenant"
    
    try:
        revenue_data = await get_revenue_summary(property_id, tenant_id)
    except RevenueDataUnavailable as e:
        # Report the outage. A dashboard that quietly shows a stand-in figure
        # is worse than one that admits it cannot answer.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Revenue data is temporarily unavailable",
        ) from e
    
    total_revenue_float = float(revenue_data['total'])
    
    return {
        "property_id": revenue_data['property_id'],
        "total_revenue": total_revenue_float,
        "currency": revenue_data['currency'],
        "reservations_count": revenue_data['count']
    }
