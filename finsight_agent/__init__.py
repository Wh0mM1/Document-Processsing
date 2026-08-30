"""FinSight AI — Context-Driven Financial Document Intelligence.

Public surface:
  build_graph()   → Compiled LangGraph pipeline
  render_report() → PDF report generator

Internal packages:
  core/       – Pydantic contracts, state schema, prompt strings
  ingestion/  – PDF parsing, chunking, embeddings
  analysis/   – Context detection, fact extraction, validation, insights, charts
  output/     – Template mapping, narrative synthesis, PDF rendering
  pipeline/   – LangGraph graph and node functions
  storage/    – SQLite document and vector store
  api/        – FastAPI REST endpoints
"""
from .pipeline.graph import build_graph
from .output.report import render_report

__all__ = ["build_graph", "render_report"]
