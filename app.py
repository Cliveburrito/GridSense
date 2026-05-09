from fastapi import FastAPI

app = FastAPI(
    title="GridSense API",
    description="Smart power grid analytics and fault management prototype.",
    version="0.1.0",
)


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