from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api.health import router as health_router
from backend.app.api.experiments import router as experiments_router
from backend.app.api.history import router as history_router
from backend.app.api.networks import router as networks_router
from backend.app.api.recovery import router as recovery_router
from backend.app.api.simulations import router as simulations_router


app = FastAPI(
    title="AquaTwin-X API",
    description="API mô phỏng và hỗ trợ phục hồi mạng lưới cấp nước",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api")
app.include_router(experiments_router, prefix="/api")
app.include_router(history_router, prefix="/api")
app.include_router(networks_router, prefix="/api")
app.include_router(simulations_router, prefix="/api")
app.include_router(recovery_router, prefix="/api")


@app.exception_handler(FileNotFoundError)
def file_not_found_handler(request: Request, exc: FileNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ValueError)
def invalid_input_handler(request: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(RuntimeError)
def simulation_runtime_handler(request: Request, exc: RuntimeError) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.get("/")
def root() -> dict[str, str]:
    return {
        "name": "AquaTwin-X API",
        "docs": "/docs",
    }

