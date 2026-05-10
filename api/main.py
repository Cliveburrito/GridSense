from contextlib import asynccontextmanager

from fastapi import FastAPI

from db import cassandra, mongo, neo4j, postgres, redis
from routers import alerts, billing, equipment, grid, sensors


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await redis.shutdown()
    await neo4j.shutdown()
    await mongo.shutdown()
    await postgres.shutdown()
    await cassandra.shutdown()


app = FastAPI(title="GridSense API", lifespan=lifespan)

app.include_router(sensors.router)
app.include_router(grid.router)
app.include_router(equipment.router)
app.include_router(billing.router)
app.include_router(alerts.router)


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "gridsense-api",
    }


@app.get("/")
async def root():
    return {
        "message": "GridSense API is running",
        "docs": "/docs",
        "health": "/health",
    }
