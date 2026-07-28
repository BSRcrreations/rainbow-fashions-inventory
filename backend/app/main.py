from __future__ import annotations

import logging
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.staticfiles import StaticFiles

from app.api.routes import auth, brands, categories, dashboard, products, purchases, sales, security, stock, subcategories, purchase_documents
from app.core.config import get_settings
from app.core.exceptions import error_payload
from app.core.logging import configure_logging


settings = get_settings()
configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.app_name,
    version="1.0.0-phase1",
    # Never expose framework tracebacks to API consumers, including local development.
    debug=False,
    openapi_url=f"{settings.api_v1_prefix}/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers.setdefault("X-Request-ID", request_id)
    return response

settings.product_upload_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads/products", StaticFiles(directory=settings.product_upload_dir), name="product_uploads")


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    detail = exc.detail
<<<<<<< HEAD
    request_id = getattr(request.state, "request_id", None)
    payload = detail.copy() if isinstance(detail, dict) and "message" in detail else error_payload(str(detail), "http_error")
    payload.setdefault("request_id", request_id)
=======
    payload = detail if isinstance(detail, dict) and "message" in detail else error_payload(str(detail), "http_error")
    payload.setdefault("request_id", getattr(request.state, "request_id", None))
>>>>>>> shop-inventory
    return JSONResponse(status_code=exc.status_code, content={"detail": payload})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    fields = [
        {"field": ".".join(str(part) for part in error["loc"] if part != "body"), "message": error["msg"]}
        for error in exc.errors()
    ]
<<<<<<< HEAD
    return JSONResponse(
        status_code=422,
        content={"detail": error_payload("Validation failed", "validation_error", fields, getattr(request.state, "request_id", None))},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, _: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=500,
        content={"detail": error_payload("The server could not complete this request. Please try again.", "internal_error", request_id=request_id)},
        headers={"X-Request-ID": request_id} if request_id else None,
    )
=======
    payload = error_payload("Validation failed", "validation_error", fields)
    payload["request_id"] = getattr(request.state, "request_id", None)
    return JSONResponse(status_code=422, content={"detail": payload})


@app.exception_handler(IntegrityError)
async def integrity_exception_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    logger.exception("Database integrity error", exc_info=exc)
    payload = error_payload("This record conflicts with existing data. Refresh and try again.", "integrity_error")
    payload["request_id"] = getattr(request.state, "request_id", None)
    return JSONResponse(status_code=409, content={"detail": payload})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled API error", exc_info=exc)
    payload = error_payload("The server could not complete this request. Please try again.", "internal_error")
    payload["request_id"] = getattr(request.state, "request_id", None)
    return JSONResponse(status_code=500, content={"detail": payload})
>>>>>>> shop-inventory

app.include_router(auth.router, prefix=settings.api_v1_prefix)
app.include_router(dashboard.router, prefix=settings.api_v1_prefix)
app.include_router(categories.router, prefix=settings.api_v1_prefix)
app.include_router(brands.router, prefix=settings.api_v1_prefix)
app.include_router(subcategories.router, prefix=settings.api_v1_prefix)
app.include_router(sales.router, prefix=settings.api_v1_prefix)
app.include_router(products.router, prefix=settings.api_v1_prefix)
app.include_router(purchases.router, prefix=settings.api_v1_prefix)
app.include_router(purchase_documents.router, prefix=settings.api_v1_prefix)
app.include_router(stock.router, prefix=settings.api_v1_prefix)
app.include_router(security.router, prefix=settings.api_v1_prefix)


@app.get("/health", tags=["System"])
def health() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name}
