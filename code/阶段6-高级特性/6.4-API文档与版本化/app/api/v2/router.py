"""V2 路由汇总"""
from fastapi import APIRouter
from app.api.v2.endpoints import users

router = APIRouter()
router.include_router(users.router, tags=["V2-用户"])
