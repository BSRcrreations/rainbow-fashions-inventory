from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, brands, categories, dashboard, products, purchases, stock
from app.core.config import get_settings
from app.core.logging import configure_logging


settings = get_settings()
configure_logging()

app = FastAPI(
    title=settings.app_name,
    version="1.0.0-phase1",
    debug=settings.debug,
    openapi_url=f"{settings.api_v1_prefix}/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=settings.api_v1_prefix)
app.include_router(dashboard.router, prefix=settings.api_v1_prefix)
app.include_router(categories.router, prefix=settings.api_v1_prefix)
app.include_router(brands.router, prefix=settings.api_v1_prefix)
app.include_router(products.router, prefix=settings.api_v1_prefix)
app.include_router(purchases.router, prefix=settings.api_v1_prefix)
app.include_router(stock.router, prefix=settings.api_v1_prefix)


@app.get("/health", tags=["System"])
def health() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name}
