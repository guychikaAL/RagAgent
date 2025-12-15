"""
Chunking Layer

Transforms LlamaIndex Documents into hierarchical node structures.

Hierarchy:
- Sections (IndexNode) - logical document divisions
- Parent Chunks (TextNode) - 250-600 tokens, semantic units
- Child Chunks (TextNode) - 80-150 tokens, atomic facts

Usage:
    from RAG.Chunking_Layer import create_chunking_pipeline
    
    chunking_pipeline = create_chunking_pipeline(
        parent_chunk_size=400,
        child_chunk_size=120
    )
    nodes = chunking_pipeline.build_nodes(document)
"""

from .chunking_layer import (
    ChunkingPipeline,
    create_chunking_pipeline,
)

__all__ = [
    "ChunkingPipeline",
    "create_chunking_pipeline",
]

