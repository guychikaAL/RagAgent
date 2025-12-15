"""
Index Layer

Builds FAISS-backed vector indexes and retrievers on top of
hierarchical nodes (Sections → Parent → Child) per CLAIM.

Critical: EMBEDDING CONSISTENCY
- ONE OpenAIEmbedding instance created here
- Used for ALL indexing and retrieval operations
- Stored in StorageContext
- Reused implicitly on load and query
- NEVER recreated or overridden

Usage:
    from RAG.Index_Layer import create_index_layer
    
    # Build indexes for ONE claim
    index_layer = create_index_layer()
    index_layer.build_indexes(nodes)
    
    # Query with Needle (precise)
    results = index_layer.query_needle("What is the account number?")
    
    # Query with Summary (contextual)
    results = index_layer.query_summary("Summarize the incident")
    
    # Persist
    index_layer.save("storage/claim_2")
    
    # Load
    loaded = IndexLayer.load("storage/claim_2")
"""

from .index_layer import (
    IndexLayer,
    create_index_layer,
    ClaimIndexManager,
)

__all__ = [
    "IndexLayer",
    "create_index_layer",
    "ClaimIndexManager",
]

