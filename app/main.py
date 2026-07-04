import os
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
# Runtime helpers
# ---------------------------------------------------------
def is_vercel_runtime() -> bool:
    """
    Detects if the app is running on Vercel.

    Vercel deploys code under /var/task, which is read-only.
    Any temporary runtime file writes should use /tmp instead.
    """

    current_file_path = str(Path(__file__).resolve())

    return bool(
        os.getenv("VERCEL")
        or os.getenv("VERCEL_ENV")
        or os.getenv("NOW_REGION")
        or os.getenv("LAMBDA_TASK_ROOT")
        or current_file_path.startswith("/var/task")
    )


# ---------------------------------------------------------
# Uploads/static files
# ---------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent


def get_uploads_dir() -> Path:
    """
    Returns the correct uploads directory for the current runtime.

    Local:
        backend/uploads

    Vercel:
        /tmp/uploads

    Note:
        /tmp on Vercel is temporary. For real production uploads,
        move image storage to Cloudinary, S3, Supabase Storage, etc.
    """

    if is_vercel_runtime():
        return Path("/tmp/uploads")

    configured_uploads = Path(settings.UPLOADS_DIR)

    if configured_uploads.is_absolute():
        return configured_uploads

    return BASE_DIR / configured_uploads


UPLOADS_DIR = get_uploads_dir()


def get_api_prefix() -> str:
    """
    Returns a safe FastAPI API prefix.

    Normal expected value:
        /api/v1

    Git Bash on Windows can sometimes convert:
        /api/v1

    into:
        /C:/Program Files/Git/api/v1

    This function repairs that so routes always register under:
        /api/v1
    """

    raw_prefix = getattr(settings, "API_V1_PREFIX", "/api/v1") or "/api/v1"
    prefix = str(raw_prefix).strip().replace("\\", "/")

    if not prefix:
        return "/api/v1"

    lower_prefix = prefix.lower()

    # Fix Git Bash / MSYS path conversion:
    # /C:/Program Files/Git/api/v1 -> /api/v1
    api_marker_index = lower_prefix.rfind("/api/")
    if ":/" in prefix and api_marker_index != -1:
        prefix = prefix[api_marker_index:]

    # If env is set as api/v1, make it /api/v1
    if not prefix.startswith("/"):
        prefix = f"/{prefix}"

    # Remove trailing slash except root
    prefix = prefix.rstrip("/")

    return prefix or "/api/v1"


API_PREFIX = get_api_prefix()


def prepare_upload_directories() -> None:
    """
    Creates upload folders used by services, products, and banners.

    This function is protected with try/except so the whole backend
    does not crash if the runtime blocks filesystem writes.
    """

    folders = [
        UPLOADS_DIR,
        UPLOADS_DIR / "services",
        UPLOADS_DIR / "products",
        UPLOADS_DIR / "banners",
    ]

    for folder in folders:
        try:
            folder.mkdir(parents=True, exist_ok=True)
            print(f"Upload folder ready: {folder}")
        except OSError as exc:
            print(f"Upload folder creation failed/skipped: {folder} | {exc}")


def mount_uploads(app: FastAPI) -> None:
    """
    Mounts uploaded files as /uploads.

    If mounting fails, the app still starts. This is important on Vercel.
    """

    try:
        prepare_upload_directories()

        app.mount(
            "/uploads",
            StaticFiles(directory=str(UPLOADS_DIR)),
            name="uploads",
        )

        print(f"Uploads mounted from: {UPLOADS_DIR}")

    except Exception as exc:
        print(f"Static uploads mount failed/skipped: {exc}")


# ---------------------------------------------------------
# Database table auto-creation
# ---------------------------------------------------------
def load_models_for_table_creation() -> None:
    """
    Import model files so SQLAlchemy registers their tables.

    Important:
    We use the catalogue model files:
        app.models.service
        app.models.product
        app.models.banner

    Do not import old duplicate service_booking or product_request files here
    if the new service.py and product.py files already include those tables.
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

    This is useful for development and early deployment.
    Later, for production, use Alembic migrations instead of automatic create_all.
    """

    try:
        load_models_for_table_creation()
        Base.metadata.create_all(bind=engine)
        print("Database tables checked/created successfully.")
    except Exception as exc:
        print(f"Database table creation failed: {exc}")


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
    mount_uploads(app)

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
            "api_prefix": API_PREFIX,
            "raw_api_prefix": getattr(settings, "API_V1_PREFIX", None),
            "uploads": "/uploads",
            "runtime": "vercel" if is_vercel_runtime() else "local",
            "uploads_dir": str(UPLOADS_DIR),
        }

    @app.get("/health", tags=["Health"])
    def health_check() -> dict[str, Any]:
        return {
            "success": True,
            "status": "healthy",
            "message": "Astra Group API is healthy.",
            "runtime": "vercel" if is_vercel_runtime() else "local",
            "uploads_dir": str(UPLOADS_DIR),
        }

    @app.get(f"{API_PREFIX}/health", tags=["Health"])
    def api_health_check() -> dict[str, Any]:
        return {
            "success": True,
            "status": "healthy",
            "message": "Astra Group API v1 is healthy.",
            "runtime": "vercel" if is_vercel_runtime() else "local",
            "api_prefix": API_PREFIX,
        }

    @app.get(f"{API_PREFIX}/db-health", tags=["Health"])
    def database_health_check() -> dict[str, Any]:
        result = test_database_connection()
        status_value = "connected" if result.get("connected") else "failed"

        return {
            "success": bool(result.get("connected")),
            "status": status_value,
            **result,
        }

    @app.get(f"{API_PREFIX}/tables", tags=["Health"])
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

    Uses find_spec first so that real import errors inside a route file
    are not silently hidden.
    """

    if find_spec(module_path) is None:
        print(f"Route not found yet, skipped: {module_path}")
        return

    try:
        module = import_module(module_path)
    except Exception as exc:
        print(f"Route import failed: {module_path} | {exc}")
        raise

    router = getattr(module, router_name, None)

    if router is None:
        print(f"No router found in: {module_path}")
        return

    app.include_router(router, prefix=API_PREFIX)
    print(f"Route loaded: {module_path} -> {API_PREFIX}")


app = create_app()