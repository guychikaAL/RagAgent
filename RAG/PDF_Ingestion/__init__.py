"""
PDF Ingestion Layer

Converts PDF files into clean LlamaIndex Documents with metadata.

Usage:
    from RAG.PDF_Ingestion import create_ingestion_pipeline
    
    pipeline = create_ingestion_pipeline(document_type="insurance_claim_form")
    document = pipeline.ingest("path/to/file.pdf")
"""

from .pdf_ingestion import (
    PDFIngestionPipeline,
    PDFIngestionError,
    create_ingestion_pipeline,
)

__all__ = [
    "PDFIngestionPipeline",
    "PDFIngestionError",
    "create_ingestion_pipeline",
]

