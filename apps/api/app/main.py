from fastapi import FastAPI

from app.health import router as health_router

app = FastAPI(title="Grocery API")
app.include_router(health_router)
