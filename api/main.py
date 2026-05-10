from fastapi import FastAPI

from routers.alerts import router as alerts_router
from routers.billing import router as billing_router
from routers.equipment import router as equipment_router
from routers.grid import router as grid_router
from routers.sensors import router as sensors_router

app = FastAPI(
    title="GridSense API",
    description="Smart power grid analytics and fault management prototype.",
    version="0.1.0",
)

app.include_router(sensors_router)
app.include_router(grid_router)
app.include_router(billing_router)
app.include_router(equipment_router)
app.include_router(alerts_router)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "gridsense-api",
    }


@app.get("/")
def root():
    return {
        "message": "GridSense API is running",
        "docs": "/docs",
        "health": "/health",
    }
