import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from life.auth import check_auth, logout, SESSION_COOKIE_NAME
from life.config import settings
from life.routers import health, webhooks, shipments
from life.storage import database
from life.tasks.scheduler import start_scheduler, shutdown_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Life Dashboard")
    database.init_db()
    start_scheduler()
    yield
    # Shutdown
    shutdown_scheduler()
    logger.info("Life Dashboard shutdown")


app = FastAPI(title="Life Dashboard", lifespan=lifespan)

# Mount static files if directory exists
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Include routers
app.include_router(health.router)
app.include_router(webhooks.router, prefix="/webhooks")
app.include_router(shipments.router, prefix="/shipments")


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Redirect to shipments or login."""
    if check_auth(request):
        return RedirectResponse(url="/shipments")
    return RedirectResponse(url="/login")


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Show login page."""
    if check_auth(request):
        return RedirectResponse(url="/shipments")
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
async def login_action(secret: str = Form(...)):
    """Handle login form submission."""
    if secret != settings.secret_key:
        raise HTTPException(status_code=401, detail="Invalid secret")

    response = RedirectResponse(url="/shipments", status_code=303)
    response.set_cookie(
        SESSION_COOKIE_NAME,
        settings.secret_key,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=60 * 60 * 24 * 30,  # 30 days
    )
    return response


@app.get("/logout")
async def logout_action():
    """Handle logout."""
    return logout()
