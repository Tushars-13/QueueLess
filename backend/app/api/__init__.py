"""API router aggregator."""

from fastapi import APIRouter

from app.api.routes import auth, business, health, queue, service, staff

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(business.router)
api_router.include_router(service.router)
api_router.include_router(staff.router)
api_router.include_router(queue.router)
