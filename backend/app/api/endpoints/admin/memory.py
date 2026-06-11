from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any
from backend.app.auth.dependencies import get_current_user

router = APIRouter()

@router.get("", response_model=List[Dict[str, Any]])
async def get_all_memories(current_user: Any = Depends(get_current_user)):
    """
    Get all memory entries for admin view.
    """
    if "admin" not in current_user.role.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
        
    # Return dummy data for now
    return [
        {"entity_id": "user-123", "content": "User prefers concise answers"},
        {"entity_id": "team-sales", "content": "Sales team focuses on monthly revenue"},
        {"entity_id": "user-456", "content": "Default timezone is EST"}
    ]
