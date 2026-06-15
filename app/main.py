from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from app.config import settings
from app.database import Base, engine
from app.routers import auth, market, portfolios, positions, risk

Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.app_name)
app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(positions.router, prefix=settings.api_prefix)
app.include_router(portfolios.router, prefix=settings.api_prefix)
app.include_router(market.router, prefix=settings.api_prefix)
app.include_router(risk.router, prefix=settings.api_prefix)

static_dir = Path(__file__).parent / "static"
templates_dir = Path(__file__).parent / "templates"
app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=str(templates_dir))

@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"app_name": settings.app_name}
    )

#@app.get("/", response_class=HTMLResponse)
#def root(request: Request):
#    return templates.TemplateResponse("index.html", {"request": request, "app_name": settings.app_name})
