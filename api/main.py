"""FIREWISE API (FastAPI). Run: .venv/bin/uvicorn api.main:app --port 8000"""
import os
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from . import copilot, models, services
from .db import connect, db_available
from .twin.routes import router as twin_router

app = FastAPI(title="FIREWISE API", version="1.0.0",
              description="Evidence-grounded access to NASA PSI combustion investigations, plus the FIREWISE Digital Twin (/api/twin). The scientific database is read-only; user scenarios live in a separate state store.")
app.add_middleware(CORSMiddleware, allow_origins=os.environ.get("FIREWISE_CORS", "http://localhost:5173,http://127.0.0.1:5173").split(","),
                   allow_methods=["GET", "POST", "PUT", "DELETE"], allow_headers=["*"])
app.include_router(twin_router)


def err(status, code, message, details=None):
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message, "details": details or {}}})


@app.exception_handler(HTTPException)
async def http_exc(_: Request, exc: HTTPException):
    code = {404: "not_found", 400: "invalid_parameter", 503: "unavailable"}.get(exc.status_code, "error")
    return err(exc.status_code, code, str(exc.detail))


@app.exception_handler(RequestValidationError)
async def val_exc(_: Request, exc: RequestValidationError):
    # Only loc/msg/type: the raw error may carry exception objects (not JSON-serialisable) and echoes the whole input.
    errors = [{"loc": [str(x) for x in e.get("loc", ())], "msg": str(e.get("msg", "")), "type": str(e.get("type", ""))} for e in exc.errors()[:5]]
    return err(422, "validation_error", "Request parameters failed validation", {"errors": errors})


@app.exception_handler(Exception)
async def any_exc(_: Request, exc: Exception):
    return err(500, "internal_error", f"{type(exc).__name__}")


def need_db():
    if not db_available():
        raise HTTPException(503, "Database not built. Run scripts/load_db.py")


@app.get("/api/health", response_model=models.Health)
def health():
    if not db_available():
        return {"status": "degraded", "build": None, "copilot_configured": copilot.llm_available(), "copilot_model": copilot.MODEL_ID}
    with connect() as con:
        return {"status": "ok", "build": services.build_info(con), "copilot_configured": copilot.llm_available(), "copilot_model": copilot.MODEL_ID}


@app.get("/api/summary", response_model=models.Summary)
def summary():
    need_db()
    with connect() as con:
        return services.summary(con)


@app.get("/api/investigations", response_model=models.InvestigationPage)
def investigations(q: Optional[str] = None, fuel_class: list[str] = Query(default=[]), platform: list[str] = Query(default=[]),
                   data_class: list[str] = Query(default=[]), o2_min: Optional[float] = None, o2_max: Optional[float] = None,
                   p_min_atm: Optional[float] = None, p_max_atm: Optional[float] = None,
                   limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0),
                   sort: str = Query("id", pattern="^(id|acronym|n_records)$")):
    need_db()
    with connect() as con:
        return services.list_investigations(con, q, fuel_class or None, platform or None, data_class or None,
                                            o2_min, o2_max, p_min_atm, p_max_atm, limit, offset, sort)


@app.get("/api/investigations/{inv_id}", response_model=models.InvestigationDetail)
def investigation(inv_id: str):
    need_db()
    with connect() as con:
        d = services.investigation_detail(con, inv_id.upper())
    if d is None:
        raise HTTPException(404, f"Unknown investigation {inv_id}")
    return d


@app.get("/api/investigations/{inv_id}/runs", response_model=models.InvestigationRuns)
def investigation_runs(inv_id: str, granularity: list[str] = Query(default=[]), include_duplicates: bool = False,
                       limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)):
    need_db()
    with connect() as con:
        if con.execute("SELECT 1 FROM investigation WHERE id=?", (inv_id.upper(),)).fetchone() is None:
            raise HTTPException(404, f"Unknown investigation {inv_id}")
        return services.investigation_runs(con, inv_id.upper(), granularity or None, include_duplicates, limit, offset)


@app.get("/api/runs", response_model=models.RunPage)
def runs(investigation_id: list[str] = Query(default=[]), fuel_class: list[str] = Query(default=[]),
         o2_context: str = Query("ambient", pattern="^(ambient|burner_stream|envelope)$"),
         o2_min: Optional[float] = Query(None, ge=0, le=100), o2_max: Optional[float] = Query(None, ge=0, le=100),
         p_min_atm: Optional[float] = Query(None, ge=0), p_max_atm: Optional[float] = Query(None, ge=0),
         documented_only: bool = False, include_duplicates: bool = False, granularity: list[str] = Query(default=[]),
         limit: int = Query(100, ge=1, le=2000), offset: int = Query(0, ge=0)):
    need_db()
    if o2_min is not None and o2_max is not None and o2_min > o2_max:
        raise HTTPException(400, "o2_min must be <= o2_max")
    with connect() as con:
        return services.search_runs(con, investigation_id or None, fuel_class or None, o2_context, o2_min, o2_max, p_min_atm, p_max_atm,
                                    documented_only, include_duplicates, granularity or None, limit, offset)


@app.get("/api/points", response_model=models.Points)
def points():
    need_db()
    with connect() as con:
        return services.points(con)


@app.get("/api/distributions", response_model=models.Distribution)
def distributions(variable: str = Query(..., pattern="^(o2_pct|p_atm|flow_cm_s)$"),
                  group_by: str = Query("fuel_class", pattern="^(fuel_class|investigation|status)$"),
                  o2_context: str = Query("ambient", pattern="^(ambient|burner_stream|envelope)$"), bins: int = Query(20, ge=2, le=100)):
    need_db()
    with connect() as con:
        return services.distributions(con, variable, group_by, o2_context, bins)


@app.get("/api/scenarios", response_model=list[models.Scenario])
def scenarios():
    need_db()
    with connect() as con:
        return services.scenario_list(con)


@app.get("/api/scenarios/{scenario_id}/evidence", response_model=models.ScenarioEvidence)
def scenario_evidence(scenario_id: str, fuel_focus: Optional[str] = Query(None, pattern="^(any|solid|gaseous|liquid_droplet|smoke_source_nonflaming)$")):
    need_db()
    s = services.SCENARIOS.get(scenario_id)
    if s is None:
        raise HTTPException(404, f"Unknown scenario {scenario_id}")
    w = dict(s["window"])
    if fuel_focus:
        w["fuel_focus"] = fuel_focus
    with connect() as con:
        return services.scenario_evidence(con, w, scenario_id, s["label"], s["description"], s["source"])


@app.post("/api/scenarios/custom/evidence", response_model=models.ScenarioEvidence)
def scenario_custom(window: models.Window):
    need_db()
    if window.o2_min_pct > window.o2_max_pct or window.p_min_psia > window.p_max_psia:
        raise HTTPException(400, "window minimum must be <= maximum")
    with connect() as con:
        return services.scenario_evidence(con, window.model_dump())


@app.get("/api/compare", response_model=models.Comparison)
def compare(ids: str = Query(..., description="2-4 comma-separated PSI ids")):
    need_db()
    lst = [i.strip().upper() for i in ids.split(",") if i.strip()]
    if not 2 <= len(lst) <= 4 or len(set(lst)) != len(lst):
        raise HTTPException(400, "Provide 2-4 distinct investigation ids")
    with connect() as con:
        known = {r[0] for r in con.execute("SELECT id FROM investigation")}
        missing = [i for i in lst if i not in known]
        if missing:
            raise HTTPException(404, f"Unknown investigation(s): {', '.join(missing)}")
        return services.compare(con, lst)


@app.get("/api/gaps", response_model=models.Gaps)
def gaps():
    need_db()
    with connect() as con:
        return services.gaps(con)


@app.get("/api/evidence/{evidence_id:path}", response_model=models.Evidence)
def evidence(evidence_id: str):
    need_db()
    with connect() as con:
        e = services.evidence(con, evidence_id)
    if e is None:
        raise HTTPException(404, f"Unknown evidence id {evidence_id}")
    return e


@app.post("/api/ask", response_model=models.AskResponse)
def ask(req: models.AskRequest):
    need_db()
    with connect() as con:
        twin = req.twin.model_dump() if req.twin else None
        try:
            return copilot.ask(con, req.question.strip(), req.scenario_id, twin=twin)
        except copilot.TwinContextError as e:
            raise HTTPException(400, str(e))


# Static frontend (Vite build of ui/ -> ui/dist) served on the same origin; API routes above take precedence.
_WEB = os.environ.get("FIREWISE_UI_DIST", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ui", "dist"))
if os.path.isdir(_WEB):
    app.mount("/", StaticFiles(directory=_WEB, html=True), name="web")
