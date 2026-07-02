from contextlib import asynccontextmanager
from importlib import import_module
from importlib.util import find_spec
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import Base, engine, test_database_connection


# ---------------------------------------------------------
# Uploads/static files
# ---------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
UPLOADS_DIR = BASE_DIR / "uploads"


def prepare_upload_directories() -> None:
    """
    Creates upload folders used by services, products, and banners.
    """

    folders = [
        UPLOADS_DIR,
        UPLOADS_DIR / "services",
        UPLOADS_DIR / "products",
        UPLOADS_DIR / "banners",
    ]

    for folder in folders:
        folder.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------
# Database table auto-creation
# ---------------------------------------------------------
def load_models_for_table_creation() -> None:
    """
    Import model files so SQLAlchemy registers their tables.

    Important:
    We now use the catalogue model files:
        app.models.service
        app.models.product
        app.models.banner

    Do not import the old app.models.service_booking or
    app.models.product_request files here, because the new service.py and
    product.py files already include those tables.
    """

    model_modules = [
        "app.models.user",
        "app.models.service",
        "app.models.product",
        "app.models.banner",
    ]

    for module_path in model_modules:
        if find_spec(module_path) is None:
            print(f"Model not found yet, skipped: {module_path}")
            continue

        import_module(module_path)
        print(f"Model loaded: {module_path}")


def create_database_tables() -> None:
    """
    Automatically creates missing database tables.

    This is useful for development. Later, for production, use Alembic
    migrations instead of automatic create_all.
    """

    load_models_for_table_creation()
    Base.metadata.create_all(bind=engine)
    print("Database tables checked/created successfully.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs when the FastAPI app starts and stops.
    """

    prepare_upload_directories()
    create_database_tables()
    yield


def create_app() -> FastAPI:
    """
    Creates and configures the Astra Group FastAPI app.
    """

    app = FastAPI(
        title=settings.APP_NAME,
        description=(
            "Backend API for Astra Group users, authentication, services, "
            "service bookings, products, product requests, frontend banners, "
            "image uploads, email, and WhatsApp workflows."
        ),
        version="1.0.0",
        debug=settings.APP_DEBUG,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ---------------------------------------------------------
    # CORS
    # ---------------------------------------------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ---------------------------------------------------------
    # Static uploaded files
    # ---------------------------------------------------------
    prepare_upload_directories()
    app.mount(
        "/uploads",
        StaticFiles(directory=str(UPLOADS_DIR)),
        name="uploads",
    )

    # ---------------------------------------------------------
    # Basic Routes
    # ---------------------------------------------------------
    @app.get("/", tags=["Root"])
    def root() -> dict[str, Any]:
        return {
            "success": True,
            "message": "Astra Group API is running.",
            "app_name": settings.APP_NAME,
            "environment": settings.APP_ENV,
            "docs": "/docs",
            "api_prefix": settings.API_V1_PREFIX,
            "uploads": "/uploads",
        }

    @app.get("/health", tags=["Health"])
    def health_check() -> dict[str, Any]:
        return {
            "success": True,
            "status": "healthy",
            "message": "Astra Group API is healthy.",
        }

    @app.get(f"{settings.API_V1_PREFIX}/health", tags=["Health"])
    def api_health_check() -> dict[str, Any]:
        return {
            "success": True,
            "status": "healthy",
            "message": "Astra Group API v1 is healthy.",
        }

    @app.get(f"{settings.API_V1_PREFIX}/db-health", tags=["Health"])
    def database_health_check() -> dict[str, Any]:
        result = test_database_connection()
        status_value = "connected" if result.get("connected") else "failed"

        return {
            "success": bool(result.get("connected")),
            "status": status_value,
            **result,
        }

    @app.get(f"{settings.API_V1_PREFIX}/tables", tags=["Health"])
    def database_tables_check() -> dict[str, Any]:
        """
        Shows SQLAlchemy registered tables.

        This confirms which models were loaded by the backend.
        """

        table_names = sorted(Base.metadata.tables.keys())

        return {
            "success": True,
            "message": "Registered SQLAlchemy tables.",
            "tables": table_names,
            "count": len(table_names),
        }

    # ---------------------------------------------------------
    # Exception Handlers
    # ---------------------------------------------------------
    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "success": False,
                "message": "The requested resource was not found.",
                "path": str(request.url.path),
            },
        )

    @app.exception_handler(500)
    async def internal_error_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "message": "Internal server error.",
                "path": str(request.url.path),
            },
        )

    # ---------------------------------------------------------
    # API Routers
    # ---------------------------------------------------------
    register_optional_router(app, "app.routes.auth", "router")
    register_optional_router(app, "app.routes.users", "router")
    register_optional_router(app, "app.routes.services", "router")
    register_optional_router(app, "app.routes.products", "router")
    register_optional_router(app, "app.routes.banners", "router")

    return app


def register_optional_router(app: FastAPI, module_path: str, router_name: str) -> None:
    """
    Loads a route module if it exists and includes it in the FastAPI app.

    This uses find_spec first so that real import errors inside a route file
    are not silently hidden.
    """

    if find_spec(module_path) is None:
        print(f"Route not found yet, skipped: {module_path}")
        return

    module = import_module(module_path)
    router = getattr(module, router_name, None)

    if router is not None:
        app.include_router(router, prefix=settings.API_V1_PREFIX)
        print(f"Route loaded: {module_path}")
    else:
        print(f"No router found in: {module_path}")


app = create_app()
