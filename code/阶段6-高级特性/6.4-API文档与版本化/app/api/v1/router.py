"""V1 路由汇总"""
from fastapi import APIRouter
from app.api.v1.endpoints import users

router = APIRouter()
router.include_router(users.router, tags=["V1-用户"])
