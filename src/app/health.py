from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def ok():
    return {"status": "ok"}
