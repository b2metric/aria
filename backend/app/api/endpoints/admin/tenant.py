from fastapi import APIRouter, Depends, HTTPException, status
from backend.app.auth.dependencies import get_current_user

from typing import Any

router = APIRouter()

@router.get("")
async def get_tenant_config(current_user: Any = Depends(get_current_user)):
    """
    Get tenant configuration limits
    """
    if "admin" not in current_user.role.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
        
    return {
        "daily_token_limit": 50000,
        "max_row_limit": 1000
    }
