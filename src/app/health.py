from fastapi import APIRouter

router = APIRouter()

@router.get("")
async def ok():
    return {"status": "ok"}
