"""
Claim Segmentation Layer

Splits multi-claim PDF documents into separate claim Documents.

WHY: Many insurance PDFs contain 20+ claims in one file.
Each claim is an independent business entity that should be
chunked, indexed, and queried separately.

Usage:
    from RAG.Claim_Segmentation import create_claim_segmentation_pipeline
    from RAG.PDF_Ingestion import create_ingestion_pipeline
    
    # Get full PDF document
    ingestion = create_ingestion_pipeline()
    document = ingestion.ingest("multi_claim.pdf")
    
    # Split into individual claims
    segmentation = create_claim_segmentation_pipeline()
    claim_documents = segmentation.split_into_claims(document)
    
    # Process each claim separately
    for claim in claim_documents:
        print(f"Claim {claim.metadata['claim_number']}")
"""

from .claim_segmentation import (
    ClaimSegmentationPipeline,
    create_claim_segmentation_pipeline,
)

__all__ = [
    "ClaimSegmentationPipeline",
    "create_claim_segmentation_pipeline",
]

