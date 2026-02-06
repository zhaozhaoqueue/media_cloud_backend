from fastapi import APIRouter

from app.api.v1.endpoints import auth, files, health, members, photos, share_codes, spaces

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(spaces.router, tags=["spaces"])
api_router.include_router(photos.router, tags=["photos"])
api_router.include_router(members.router, tags=["members"])
api_router.include_router(share_codes.router, tags=["share-codes"])
api_router.include_router(files.router, tags=["files"])
