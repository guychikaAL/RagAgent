"""
RAG Agent v2 - Production-Grade RAG System

A modular, scalable RAG system built with:
- LlamaIndex for RAG primitives
- LangChain for agents and orchestration
- FAISS for vector storage
- OpenAI for embeddings and LLM

Architecture:
1. PDF Ingestion Layer - PDF → Document
2. Chunking Layer - Document → Hierarchical Nodes
3. Index Layer - Nodes → VectorStoreIndex + SummaryIndex
4. Agents Layer - Router + Needle + Summary agents
5. Orchestration Layer - LangChain pipeline
"""

__version__ = "2.0.0"

