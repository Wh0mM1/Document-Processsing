from __future__ import annotations
import uuid
from pathlib import Path
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from finsight_agent.graph import build_graph
from finsight_agent.report import render_report
app = FastAPI(title="FinSight AI")


@app.post('/api/uploads')
async def upload(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(415, 'Upload a PDF')
    run_id = str(uuid.uuid4())
    source = Path('data/uploads')/f'{run_id}.pdf'
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(await file.read())
    result = build_graph().invoke({'source_path': str(source), 'run_id': run_id}, {
        'configurable': {'thread_id': run_id}})
    report = render_report(result, f'data/reports/{run_id}.pdf')
    return {'run_id': run_id, 'status': result['status'], 'document_id': result['document_id'], 'summary': {'structured_data': result.get('structured_data', []), 'narrative_sections': result.get('narrative_sections', []), 'quality_flags': result.get('quality_flags', []), 'llm_summary': result.get('llm_summary', {})}, 'report_url': f'/api/reports/{run_id}', 'document_url': f'/api/documents/{result["document_id"]}'}


@app.get('/api/documents/{document_id}')
def document(document_id: str):
    import json
    import sqlite3
    con = sqlite3.connect('data/finsight.sqlite3')
    row = con.execute(
        'SELECT manifest FROM documents WHERE id=?', (document_id,)).fetchone()
    if not row or not row[0]:
        raise HTTPException(404, 'Document not found')
    return json.loads(row[0])


@app.get('/api/reports/{run_id}')
def download(run_id: str):
    path = Path(f'data/reports/{run_id}.pdf')
    if not path.exists():
        raise HTTPException(404, 'Report not found')
    return FileResponse(path, media_type='application/pdf', filename='finsight-report.pdf')
