from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import get_current_user_id
from app.schemas.transaction import ParseRequest, ParsedTransaction
from app.services.claude_parser import parse_transaction_text

router = APIRouter(prefix="/parse", tags=["parse"])


@router.post("/", response_model=ParsedTransaction)
async def parse_natural_language(
    payload: ParseRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Parse a natural language transaction description using Claude.

    Returns a structured transaction object for the client to review and
    confirm before saving. Does NOT persist anything — the client calls
    POST /transactions once the user confirms.
    """
    try:
        parsed = await parse_transaction_text(payload.text, today=date.today())
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    return parsed
