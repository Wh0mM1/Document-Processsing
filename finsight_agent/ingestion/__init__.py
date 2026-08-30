"""PDF ingestion, chunking, and embedding sub-package."""
from .pdf_parser import analyse_pdf, table_to_markdown, IngestionError
from .chunking import structure_aware_chunks
from .embeddings import configured_embeddings, HashEmbeddingProvider

__all__ = [
    "analyse_pdf",
    "table_to_markdown",
    "IngestionError",
    "structure_aware_chunks",
    "configured_embeddings",
    "HashEmbeddingProvider",
]
