"""Route handlers for LexAd.

Routes only receive parameters, call services, and return pages or JSON.
No complex business logic lives here.
"""

from __future__ import annotations

from fastapi import APIRouter, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app.core.config import DATA_DIR, TEMPLATES_DIR
from app.schemas.models import StandardResponse
from app.services.pipeline import run_full_pipeline
from app.utils.file_handler import validate_image_extension
from app.utils.json_reader import read_json_list

router = APIRouter()

_templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# In-memory store for demo purposes (resets on restart)
_result_store: dict[str, StandardResponse] = {}


# ── Pages ──────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page with project introduction and navigation."""
    return _templates.TemplateResponse(request, "index.html")


@router.get("/review", response_class=HTMLResponse)
async def review_page(request: Request):
    """Review page with text input, image upload, and submit."""
    return _templates.TemplateResponse(request, "review.html")


@router.get("/cases", response_class=HTMLResponse)
async def cases_page(request: Request):
    """Case library display page."""
    cases = read_json_list(DATA_DIR / "case_library.json")
    return _templates.TemplateResponse(request, "cases.html", {"cases": cases})


@router.get("/templates", response_class=HTMLResponse)
async def templates_page(request: Request):
    """Template library display page."""
    templates = read_json_list(DATA_DIR / "rewrite_templates.json")
    return _templates.TemplateResponse(request, "templates.html", {"templates": templates})


@router.get("/result/{request_id}", response_class=HTMLResponse)
async def result_page(request: Request, request_id: str):
    """Final result page showing complete standardized JSON."""
    result = _result_store.get(request_id)
    return _templates.TemplateResponse(
        request, "result.html", {"result": result, "request_id": request_id}
    )


# ── Actions ────────────────────────────────────────────────────────────────

@router.post("/review/submit")
async def review_submit(
    request: Request,
    raw_text: str = Form(default=""),
    image_file: UploadFile | None = None,
):
    """Submit review form. Returns HTMX partial or full page based on header."""
    result = run_full_pipeline(raw_text, image_file)
    _result_store[result.request_id] = result

    ctx = {"result": result}
    if request.headers.get("HX-Request"):
        return _templates.TemplateResponse(request, "partials/review_result.html", ctx)
    return _templates.TemplateResponse(request, "review.html", ctx)


@router.post("/preprocess/image")
async def preprocess_image(image_file: UploadFile | None = None):
    """Standalone image preprocess endpoint. Returns JSON."""
    from app.services.preprocess import run_preprocess
    preprocess = run_preprocess("", image_file)
    return preprocess.model_dump()


# ── HTMX Partials ──────────────────────────────────────────────────────────

@router.get("/partial/review-result", response_class=HTMLResponse)
async def partial_review_result(request: Request, raw_text: str = ""):
    """HTMX partial: review result fragment."""
    result = run_full_pipeline(raw_text, None)
    _result_store[result.request_id] = result
    return _templates.TemplateResponse(
        request, "partials/review_result.html", {"result": result}
    )


@router.get("/partial/cases", response_class=HTMLResponse)
async def partial_cases(request: Request):
    """HTMX partial: case library fragment."""
    cases = read_json_list(DATA_DIR / "case_library.json")
    return _templates.TemplateResponse(
        request, "partials/cases_list.html", {"cases": cases}
    )


@router.get("/partial/templates", response_class=HTMLResponse)
async def partial_templates(request: Request):
    """HTMX partial: template library fragment."""
    templates = read_json_list(DATA_DIR / "rewrite_templates.json")
    return _templates.TemplateResponse(
        request, "partials/templates_list.html", {"templates": templates}
    )


@router.get("/partial/final-result", response_class=HTMLResponse)
async def partial_final_result(request: Request, request_id: str = ""):
    """HTMX partial: final result fragment."""
    result = _result_store.get(request_id)
    return _templates.TemplateResponse(
        request,
        "partials/final_result.html",
        {"result": result, "request_id": request_id},
    )


# ── JSON API ───────────────────────────────────────────────────────────────

@router.get("/api/result/{request_id}")
async def api_result(request_id: str):
    """Return the full standardized JSON for a request."""
    result = _result_store.get(request_id)
    if result is None:
        return JSONResponse({"error": "not_found"}, status_code=404)
    return result.model_dump()
