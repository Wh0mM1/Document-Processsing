"""FastAPI REST API and Web UI Server for FinSight AI.

Endpoints:
  POST   /api/uploads                  – Upload a PDF; returns run results + report URL (overrides older report for duplicates)
  GET    /api/reports                  – List all uploaded documents with their single latest generated report
  GET    /api/reports/{run_id}         – Stream or download the generated PDF report (inline by default, attachment if download=true)
  GET    /api/reports/{run_id}/summary – Retrieve full structured JSON summary for a run
  PATCH  /api/reports/{run_id}/status  – Manually update report verification status (e.g. human reviewer approval)
  GET    /api/documents/{doc_id}       – Retrieve raw document manifest (JSON)
  GET    /api/documents/{doc_id}/pdf   – Stream the original source PDF for preview (inline by default, attachment if download=true)
  DELETE /api/documents/{doc_id}       – Delete a document, its extracted assets, and its generated report
  POST   /api/clear-all                – Clear all database records and storage files
  GET    /api/stats                    – Overall document & report analytics
  GET    /                             – Modern Web UI application
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from ..pipeline.graph import build_graph
from ..output.report import render_report
from ..storage.store import SQLiteResearchStore

app = FastAPI(title="FinSight AI Document Intelligence", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_UPLOAD_DIR = Path("data/uploads")
_REPORT_DIR = Path("data/reports")
_DOCS_DIR = Path("data/documents")
_DB_PATH = Path("data/finsight.sqlite3")
_STATIC_DIR = Path("static")

_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
_REPORT_DIR.mkdir(parents=True, exist_ok=True)
_DOCS_DIR.mkdir(parents=True, exist_ok=True)
_STATIC_DIR.mkdir(parents=True, exist_ok=True)


def _get_db():
    con = sqlite3.connect(str(_DB_PATH), check_same_thread=False, timeout=30.0)
    con.row_factory = sqlite3.Row
    return con


def _find_original_pdf(doc_id: str, source_path: str | None = None) -> Path | None:
    """Find the single source PDF for a document, prioritizing data/uploads."""
    candidates = [
        _UPLOAD_DIR / f"{doc_id}.pdf",
        _DOCS_DIR / doc_id / "original.pdf",
    ]
    if source_path:
        try:
            candidates.append(Path(source_path))
        except Exception:
            pass
    for c in candidates:
        try:
            if c.exists() and c.is_file():
                return c
        except Exception:
            pass
    return None


@app.post("/api/uploads")
async def upload(file: UploadFile = File(...)):
    """Accept a PDF, deduplicate by SHA-256 hash, process through the pipeline,
    and return structured analysis + download URL for the PDF report.
    If the document was uploaded previously, the latest report overrides older reports."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(415, "Please upload a valid PDF file.")

    content = await file.read()
    doc_hash = hashlib.sha256(content).hexdigest()

    # 1. Clean up older PDF reports for this document if it was previously processed
    with _get_db() as con:
        old_runs = con.execute("SELECT id FROM runs WHERE document_id=?", (doc_hash,)).fetchall()
        for old_row in old_runs:
            old_pdf = _REPORT_DIR / f"{old_row['id']}.pdf"
            if old_pdf.exists():
                try:
                    old_pdf.unlink()
                except Exception:
                    pass

    # 2. Store single original PDF file
    _UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    source = _UPLOAD_DIR / f"{doc_hash}.pdf"
    source.write_bytes(content)

    # 3. Run pipeline
    run_id = str(uuid.uuid4())
    result = build_graph().invoke(
        {"source_path": str(source), "run_id": run_id, "original_filename": file.filename},
        {"configurable": {"thread_id": run_id}},
    )

    if "original_filename" not in result:
        result["original_filename"] = file.filename

    # 4. Render single latest PDF report
    _REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_file = _REPORT_DIR / f"{run_id}.pdf"
    try:
        render_report(result, str(report_file))
    except Exception as e:
        print(f"Warning: report rendering failed for {run_id}: {e}")

    # 5. Save run in SQLite (overwriting older runs for this doc)
    store = SQLiteResearchStore()
    store.save_run(run_id, result["document_id"], result["status"], result)

    return {
        "run_id": run_id,
        "status": result["status"],
        "document_id": result["document_id"],
        "filename": file.filename,
        "business_context": result.get("business_context", {}),
        "template_mapping": result.get("template_mapping", {}),
        "summary": {
            "structured_data": result.get("structured_data", []),
            "validated_facts": result.get("validated_facts", []),
            "narrative_sections": result.get("narrative_sections", []),
            "quality_flags": result.get("quality_flags", []),
            "llm_summary": result.get("llm_summary", {}),
        },
        "chart_specs": result.get("chart_specs", []),
        "observability_log": result.get("observability_log", []),
        "report_url": f"/api/reports/{run_id}",
        "download_url": f"/api/reports/{run_id}?download=true",
        "original_pdf_url": f"/api/documents/{result['document_id']}/pdf",
        "document_url": f"/api/documents/{result['document_id']}",
    }


@app.get("/api/reports")
def list_reports():
    """Returns all documents that are present in uploads with their single latest generated report.
    Only documents that actually have an uploaded source file on disk are returned."""
    with _get_db() as con:
        doc_rows = con.execute("SELECT id, source_path, manifest FROM documents").fetchall()
        docs_map: dict[str, dict[str, Any]] = {}
        for r in doc_rows:
            manifest_data = {}
            if r["manifest"]:
                try:
                    manifest_data = json.loads(r["manifest"])
                except Exception:
                    pass
            docs_map[r["id"]] = {
                "document_id": r["id"],
                "source_path": r["source_path"],
                "page_count": len(manifest_data.get("pages", [])),
                "sections_count": len(manifest_data.get("sections", [])),
                "warnings": manifest_data.get("warnings", []),
            }

        # Fetch runs ordered by rowid DESC (latest first)
        run_rows = con.execute(
            "SELECT rowid, id, document_id, status, result FROM runs ORDER BY rowid DESC"
        ).fetchall()

    # Map runs to documents (1 latest run per document)
    grouped_runs: dict[str, dict[str, Any]] = {}
    for row in run_rows:
        doc_id = row["document_id"]
        if doc_id in grouped_runs:
            continue  # only keep the latest run

        res_data = {}
        if row["result"]:
            try:
                res_data = json.loads(row["result"])
            except Exception:
                pass

        report_path = _REPORT_DIR / f"{row['id']}.pdf"
        has_pdf = report_path.exists()

        ctx = res_data.get("business_context", {})
        llm_sum = res_data.get("llm_summary", {})
        structured = res_data.get("structured_data", [])

        headline_metrics: list[dict[str, str]] = []
        for fact in structured[:4]:
            if fact.get("metric") and fact.get("value"):
                headline_metrics.append({
                    "label": str(fact.get("metric")).replace("_", " ").title(),
                    "value": str(fact.get("value")),
                    "period": str(fact.get("period") or ""),
                })

        grouped_runs[doc_id] = {
            "run_id": row["id"],
            "rowid": row["rowid"],
            "document_id": doc_id,
            "status": row["status"],
            "has_pdf_report": has_pdf,
            "report_url": f"/api/reports/{row['id']}",
            "download_url": f"/api/reports/{row['id']}?download=true",
            "filename": res_data.get("original_filename"),
            "company_name": ctx.get("company") or res_data.get("company_name"),
            "sector": ctx.get("sector", "Financial & Operational Analysis"),
            "period": ctx.get("period", "Latest Disclosures"),
            "document_type": ctx.get("document_type", "Earnings Presentation"),
            "executive_summary": llm_sum.get("executive_summary") or llm_sum.get("text") or (
                res_data.get("narrative_sections", [{}])[0].get("title", "") if res_data.get("narrative_sections") else ""
            ),
            "headline_metrics": headline_metrics,
            "chart_count": len(res_data.get("chart_specs", [])),
            "table_count": len(res_data.get("structured_data", [])),
            "quality_flags": res_data.get("quality_flags", []),
        }

    reports_list = []
    for doc_id, latest_run in grouped_runs.items():
        doc_meta = docs_map.get(doc_id, {"document_id": doc_id, "page_count": 0})
        
        # Check that original PDF is physically present on disk
        orig_pdf = _find_original_pdf(doc_id, doc_meta.get("source_path"))
        if not orig_pdf or not orig_pdf.exists():
            continue  # Only show documents present in uploaded storage

        file_size = orig_pdf.stat().st_size

        friendly_filename = (
            latest_run.get("filename")
            or (Path(doc_meta.get("source_path", "")).name if doc_meta.get("source_path") else None)
            or f"{latest_run.get('company_name', 'Document')}.pdf"
        )

        reports_list.append({
            "document_id": doc_id,
            "filename": friendly_filename,
            "company_name": latest_run.get("company_name") or friendly_filename.replace(".pdf", ""),
            "sector": latest_run.get("sector"),
            "period": latest_run.get("period"),
            "document_type": latest_run.get("document_type"),
            "page_count": doc_meta.get("page_count", 0),
            "file_size_bytes": file_size,
            "original_pdf_url": f"/api/documents/{doc_id}/pdf",
            "original_download_url": f"/api/documents/{doc_id}/pdf?download=true",
            "has_original_pdf": True,
            "latest_run": latest_run,
        })

    # Sort documents by latest run rowid descending
    reports_list.sort(key=lambda x: x["latest_run"]["rowid"], reverse=True)

    return {
        "count": len(reports_list),
        "documents": reports_list,
    }


@app.get("/api/reports/{run_id}")
def download_report(run_id: str, download: bool = Query(False, description="Set to true to force attachment download")):
    """Stream or download the generated PDF report.
    By default (download=False), returns 'Content-Disposition: inline' so the browser displays it in iframes/viewers.
    When download=True, returns 'Content-Disposition: attachment' so the file downloads."""
    path = _REPORT_DIR / f"{run_id}.pdf"
    if not path.exists():
        with _get_db() as con:
            row = con.execute("SELECT result FROM runs WHERE id=?", (run_id,)).fetchone()
        if row and row["result"]:
            try:
                res = json.loads(row["result"])
                render_report(res, str(path))
            except Exception as e:
                raise HTTPException(500, f"Failed to render report on demand: {e}")
        else:
            raise HTTPException(404, "Report not found.")

    filename = f"finsight-report-{run_id[:8]}.pdf"
    disposition_type = "attachment" if download else "inline"

    return FileResponse(
        path,
        media_type="application/pdf",
        filename=filename,
        content_disposition_type=disposition_type,
    )


@app.get("/api/reports/{run_id}/summary")
def get_run_summary(run_id: str):
    """Return the structured JSON payload for a run."""
    with _get_db() as con:
        row = con.execute("SELECT document_id, status, result FROM runs WHERE id=?", (run_id,)).fetchone()
    if not row or not row["result"]:
        raise HTTPException(404, "Run summary not found.")
    
    data = json.loads(row["result"])
    return {
        "run_id": run_id,
        "document_id": row["document_id"],
        "status": row["status"],
        "data": data,
        "report_url": f"/api/reports/{run_id}",
        "download_url": f"/api/reports/{run_id}?download=true",
        "original_pdf_url": f"/api/documents/{row['document_id']}/pdf",
    }


@app.patch("/api/reports/{run_id}/status")
def update_report_status(
    run_id: str,
    status: str = Query(..., description="Status: 'complete' (Verified) or 'needs_review'")
):
    """Allows human reviewers/analysts to manually approve/verify a report and update its status."""
    if status not in ("complete", "needs_review"):
        raise HTTPException(400, "Invalid status. Must be 'complete' or 'needs_review'.")

    store = SQLiteResearchStore()
    with _get_db() as con:
        row = con.execute("SELECT id FROM runs WHERE id=?", (run_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Report run not found.")

    store.update_run_status(run_id, status)
    return {
        "success": True,
        "run_id": run_id,
        "status": status,
        "message": f"Report status updated to '{status}'.",
    }


@app.get("/api/documents/{document_id}/pdf")
def get_original_pdf(document_id: str, download: bool = Query(False, description="Set to true to force attachment download")):
    """Stream the original source PDF for in-browser preview (inline by default)."""
    with _get_db() as con:
        row = con.execute("SELECT source_path FROM documents WHERE id=?", (document_id,)).fetchone()
    
    source_path = row["source_path"] if row else None
    pdf_path = _find_original_pdf(document_id, source_path)
    
    if not pdf_path or not pdf_path.exists():
        raise HTTPException(404, "Original document PDF not found.")
    
    filename = f"source-{document_id[:8]}.pdf"
    disposition_type = "attachment" if download else "inline"

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=filename,
        content_disposition_type=disposition_type,
    )


@app.delete("/api/documents/{document_id}")
def delete_document(document_id: str):
    """Completely delete a document, all its database entries, extracted assets, and generated PDF reports."""
    store = SQLiteResearchStore()
    
    # 1. Find runs associated with this document to delete their PDF reports
    with _get_db() as con:
        runs = con.execute("SELECT id FROM runs WHERE document_id=?", (document_id,)).fetchall()
        for r in runs:
            r_pdf = _REPORT_DIR / f"{r['id']}.pdf"
            if r_pdf.exists():
                try:
                    r_pdf.unlink()
                except Exception:
                    pass

    # 2. Delete database records
    store.delete_document(document_id)

    # 3. Delete files from disk
    upload_file = _UPLOAD_DIR / f"{document_id}.pdf"
    if upload_file.exists():
        try:
            upload_file.unlink()
        except Exception:
            pass

    doc_dir = _DOCS_DIR / document_id
    if doc_dir.exists():
        try:
            shutil.rmtree(doc_dir)
        except Exception:
            pass

    return {
        "success": True,
        "message": f"Document {document_id} and its associated report were deleted successfully.",
        "document_id": document_id,
    }


@app.post("/api/clear-all")
def clear_all_data():
    """Clear all database records and storage directories."""
    store = SQLiteResearchStore()
    store.clear_all()

    for d in [_REPORT_DIR, _UPLOAD_DIR, _DOCS_DIR]:
        if d.exists():
            for item in d.iterdir():
                if item.name in (".gitkeep", ".DS_Store"):
                    continue
                if item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                else:
                    try:
                        item.unlink()
                    except Exception:
                        pass
        d.mkdir(parents=True, exist_ok=True)

    return {
        "success": True,
        "message": "All database records, uploaded files, and generated reports have been cleared.",
    }


@app.get("/api/documents/{document_id}")
def get_document(document_id: str):
    """Return the raw JSON manifest for an ingested document."""
    with _get_db() as con:
        row = con.execute("SELECT manifest FROM documents WHERE id=?", (document_id,)).fetchone()
    if not row or not row["manifest"]:
        raise HTTPException(404, "Document manifest not found.")
    return json.loads(row["manifest"])


@app.get("/api/stats")
def get_stats():
    """Return platform overview stats based on currently uploaded documents."""
    reports_data = list_reports()
    docs = reports_data.get("documents", [])
    
    total_docs = len(docs)
    total_reports = total_docs
    complete_count = sum(1 for d in docs if d.get("latest_run", {}).get("status") == "complete")
    review_count = sum(1 for d in docs if d.get("latest_run", {}).get("status") == "needs_review")
    total_tables = sum(d.get("latest_run", {}).get("table_count", 0) for d in docs)

    with _get_db() as con:
        chunks_count = con.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]

    return {
        "total_documents": total_docs,
        "total_reports": total_reports,
        "complete_reports": complete_count,
        "review_reports": review_count,
        "indexed_chunks": chunks_count,
        "extracted_tables": total_tables,
    }


@app.get("/", response_class=HTMLResponse)
def index_page():
    index_file = _STATIC_DIR / "index.html"
    if index_file.exists():
        return HTMLResponse(content=index_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>FinSight AI</h1><p>UI loading...</p>")


app.mount("/static", StaticFiles(directory="static"), name="static")
