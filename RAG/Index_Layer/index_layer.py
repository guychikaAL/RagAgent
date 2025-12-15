"""
====================================================
INDEX LAYER
====================================================

RESPONSIBILITY:
This layer builds all retrieval infrastructure on top of
hierarchical Nodes (Sections → Parent → Child) per CLAIM.

Creates:
- Embeddings (OpenAI, ONCE)
- FAISS vector indexes
- Needle Retriever (high precision)
- Summary Retriever (high recall)
- Persistence (save/load)

NO agents.
NO LangChain.

INPUT:
- List[BaseNode] for ONE claim
  (from Chunking Layer)

OUTPUT:
- VectorStoreIndex (FAISS)
- SummaryIndex
- Retrievers (Needle, Summary)
- Save/Load methods

====================================================
CRITICAL: EMBEDDING CONSISTENCY
====================================================

⚠️ ABSOLUTE RULE:

The SAME OpenAI embedding configuration MUST be used for:
- Index construction
- All query-time retrieval
- All retrievers
- All agents downstream

WHY:
- Different embeddings produce incompatible vector spaces
- Mixing embeddings DESTROYS retrieval quality
- Same text → same vector → correct similarity matching

HOW:
- Create ONE OpenAIEmbedding instance
- Store in StorageContext
- Reuse implicitly on load and query
- NEVER recreate or override

Violating this rule INVALIDATES the entire system.

====================================================
"""

import os
import json
from pathlib import Path
from typing import List, Optional, Dict

import faiss  # type: ignore[import]
from llama_index.core import (
    VectorStoreIndex,
    SummaryIndex,
    StorageContext,
    load_index_from_storage,
    get_response_synthesizer,
)
from llama_index.core.schema import BaseNode, TextNode, IndexNode
from llama_index.core.embeddings import BaseEmbedding
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.vector_stores.faiss import FaissVectorStore
from llama_index.core.retrievers import VectorIndexRetriever, AutoMergingRetriever
from llama_index.core.response_synthesizers import ResponseMode
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.llms.openai import OpenAI as LlamaIndexOpenAI


class IndexLayer:
    """
    Production-grade index layer for single-claim retrieval.
    
    Builds FAISS-backed vector indexes and retrievers on top of
    hierarchical nodes (Sections → Parent → Child) for ONE claim.
    
    WHY THIS EXISTS:
    - Each claim needs independent retrieval infrastructure
    - Supports both precise (needle) and contextual (summary) queries
    - Enables save/load for production deployment
    - Enforces embedding consistency across the system
    
    WHY SINGLE-CLAIM:
    - Each claim is an independent business entity
    - Prevents mixing facts across claims
    - Enables claim-specific filtering
    - Allows per-claim index optimization
    
    CRITICAL: EMBEDDING CONSISTENCY
    - ONE OpenAIEmbedding instance created here
    - Used for ALL indexing and retrieval
    - Stored in StorageContext
    - Reused implicitly on load
    - NEVER recreated or overridden
    """
    
    def __init__(
        self,
        embedding_model: str = "text-embedding-3-small",
        vector_dimension: int = 1536,
        llm_model: str = "gpt-4o-mini",
        llm_temperature: float = 0.2,
    ):
        """
        Initialize the index layer.
        
        Args:
            embedding_model: OpenAI embedding model name
            vector_dimension: Embedding dimension (1536 for text-embedding-3-small)
            llm_model: OpenAI LLM model for MapReduce synthesis
            llm_temperature: LLM temperature for synthesis (0.2 = coherent)
        
        WHY THESE DEFAULTS:
        - text-embedding-3-small: Good balance of quality and cost
        - 1536 dimensions: Standard for this model
        - gpt-4o-mini: Fast, cheap, good for summarization
        - temperature=0.2: Coherent synthesis without creativity
        - Can be overridden for text-embedding-3-large (3072 dims)
        """
        self.embedding_model = embedding_model
        self.vector_dimension = vector_dimension
        self.llm_model = llm_model
        self.llm_temperature = llm_temperature
        
        # THE SINGLE EMBEDDING INSTANCE (created lazily)
        # WHY: Embedding creation requires OpenAI API key
        # Will be initialized in build_indexes()
        self._embed_model: Optional[BaseEmbedding] = None
        
        # THE SINGLE LLM INSTANCE (for MapReduce)
        # WHY: LLM is used by MapReduce response synthesizer
        # Will be initialized lazily
        self._llm: Optional[LlamaIndexOpenAI] = None
        
        # Indexes (created during build)
        self.vector_index: Optional[VectorStoreIndex] = None
        self.summary_index: Optional[SummaryIndex] = None
        
        # Storage context (contains FAISS store + embedding)
        self.storage_context: Optional[StorageContext] = None
        
        # Claim metadata
        self.claim_id: Optional[str] = None
        self.claim_number: Optional[str] = None
    
    def _get_or_create_embedding(self) -> BaseEmbedding:
        """
        Get or create THE SINGLE embedding instance.
        
        WHY THIS METHOD:
        - Ensures embedding is created exactly once
        - Lazy initialization (only when needed)
        - Reuses same instance across all operations
        
        Returns:
            The single OpenAIEmbedding instance
        """
        if self._embed_model is None:
            # Create THE SINGLE embedding instance
            # WHY: This is the ONLY embedding used in the entire system
            self._embed_model = OpenAIEmbedding(
                model=self.embedding_model,
                embed_batch_size=100,  # Batch for efficiency
            )
            
            print(f"✅ Created embedding model: {self.embedding_model}")
            print(f"   This is the SINGLE embedding instance for all operations")
        
        return self._embed_model
    
    def _get_or_create_llm(self) -> LlamaIndexOpenAI:
        """
        Get or create THE SINGLE LLM instance for MapReduce.
        
        WHY THIS METHOD:
        - Ensures LLM is created exactly once
        - Lazy initialization (only when needed)
        - Reuses same instance for all MapReduce operations
        
        Returns:
            The single LlamaIndexOpenAI instance
        """
        if self._llm is None:
            # Create THE SINGLE LLM instance
            # WHY: Used by MapReduce response synthesizer
            self._llm = LlamaIndexOpenAI(
                model=self.llm_model,
                temperature=self.llm_temperature,
            )
            
            print(f"✅ Created LLM: {self.llm_model}")
            print(f"   Temperature: {self.llm_temperature}")
            print(f"   Used for: MapReduce summarization")
        
        return self._llm
    
    def build_indexes(
        self,
        nodes: List[BaseNode],
        claim_id: Optional[str] = None,
        claim_number: Optional[str] = None,
    ) -> None:
        """
        Build all indexes for ONE claim's nodes.
        
        This is the main entry point for index construction.
        
        Args:
            nodes: Hierarchical nodes for ONE claim
                   (from Chunking Layer)
            claim_id: Claim identifier (optional, extracted from nodes if not provided)
            claim_number: Claim number (optional)
        
        WHY THIS METHOD:
        - Centralizes all index building
        - Enforces embedding consistency
        - Creates both vector and summary indexes
        - Prepares retrievers
        """
        # Extract claim metadata
        if not nodes:
            raise ValueError("Cannot build indexes: no nodes provided")
        
        # Get claim_id from nodes if not provided
        if claim_id is None:
            claim_id = nodes[0].metadata.get('claim_id', 'unknown')
        if claim_number is None:
            claim_number = nodes[0].metadata.get('claim_number', 'unknown')
        
        self.claim_id = claim_id
        self.claim_number = claim_number
        
        print(f"📦 Building indexes for Claim #{claim_number}")
        print(f"   Claim ID: {claim_id}")
        print(f"   Total nodes: {len(nodes)}")
        
        # Stage 1: Get THE SINGLE embedding instance
        # WHY: This embedding will be used for ALL operations
        embed_model = self._get_or_create_embedding()
        
        # Stage 2: Create FAISS vector store
        # WHY: FAISS is fast, efficient, and supports similarity search
        faiss_index = faiss.IndexFlatL2(self.vector_dimension)
        vector_store = FaissVectorStore(faiss_index=faiss_index)
        
        # Stage 3: Create StorageContext with embedding
        # WHY: StorageContext stores the embedding and vector store
        # All indexes created from this context will use the SAME embedding
        self.storage_context = StorageContext.from_defaults(
            vector_store=vector_store,
        )
        
        print(f"✅ Created FAISS vector store (dimension: {self.vector_dimension})")
        
        # Stage 4: Filter nodes for vector indexing
        # WHY: We want to index TextNodes (parent + child), not IndexNodes (sections)
        text_nodes = [n for n in nodes if isinstance(n, TextNode)]
        index_nodes = [n for n in nodes if isinstance(n, IndexNode)]
        
        print(f"   TextNodes: {len(text_nodes)} (will be embedded)")
        print(f"   IndexNodes: {len(index_nodes)} (structural only)")
        
        # Stage 5: Build VectorStoreIndex
        # WHY: VectorStoreIndex enables similarity-based retrieval
        # CRITICAL: Pass embed_model explicitly to ensure consistency
        self.vector_index = VectorStoreIndex(
            nodes=text_nodes,
            storage_context=self.storage_context,
            embed_model=embed_model,  # THE SINGLE EMBEDDING
            show_progress=True,
        )
        
        print(f"✅ Built VectorStoreIndex with {len(text_nodes)} nodes")
        
        # Stage 6: Build SummaryIndex
        # WHY: SummaryIndex enables hierarchical summarization
        # Used for high-level claim understanding
        self.summary_index = SummaryIndex(
            nodes=text_nodes,
            embed_model=embed_model,  # THE SINGLE EMBEDDING (consistency!)
            show_progress=True,
        )
        
        print(f"✅ Built SummaryIndex with {len(text_nodes)} nodes")
        print(f"✅ Index building complete for Claim #{claim_number}")
    
    def get_needle_retriever(
        self,
        top_k: int = 5,
        similarity_threshold: float = 0.7,
    ):
        """
        Get Needle Retriever (high precision, child chunks only).
        
        WHY NEEDLE:
        - For precise, fact-based queries
        - Uses child chunks (atomic facts)
        - Applies similarity threshold
        - Returns only high-confidence matches
        
        Args:
            top_k: Number of chunks to retrieve
            similarity_threshold: Minimum similarity score (0-1)
                                 Only chunks above this are returned
        
        Returns:
            Configured retriever for needle queries
            
        WHY SIMILARITY THRESHOLD:
        - Prevents low-quality matches
        - "If not found, say so" behavior
        - Applied at QUERY TIME, not indexing time
        """
        if self.vector_index is None:
            raise ValueError("Index not built. Call build_indexes() first.")
        
        # Create base vector retriever for child chunks
        # WHY: VectorIndexRetriever does similarity search on child chunks
        # CRITICAL: Uses the embedding from vector_index (consistency!)
        base_retriever = VectorIndexRetriever(
            index=self.vector_index,
            similarity_top_k=top_k,
        )
        
        # Wrap with AutoMergingRetriever
        # WHY: If child chunks match, automatically return parent chunks with more context
        # This is the key pattern: Child chunks for precision → Parent chunks for context
        auto_merging_retriever = AutoMergingRetriever(
            base_retriever,
            self.vector_index.storage_context,
            verbose=False,  # Set to True for debugging
        )
        
        print(f"🎯 Needle Retriever configured:")
        print(f"   Mode: AUTO-MERGING (child → parent)")
        print(f"   Top-k: {top_k} (child chunks searched)")
        print(f"   Similarity threshold: {similarity_threshold}")
        print(f"   Returns: Parent chunks with full context")
        print(f"   Uses embedding: {self.embedding_model}")
        
        return auto_merging_retriever
    
    def get_summary_retriever(
        self,
        top_k: int = 8,
    ):
        """
        Get Summary Retriever (high recall, parent + child chunks).
        
        WHY SUMMARY:
        - For broad, contextual queries
        - Uses parent AND child chunks
        - NO similarity threshold (high recall)
        - Enables auto-merging (child → parent)
        
        Args:
            top_k: Number of chunks to retrieve
        
        Returns:
            Configured retriever for summary queries
            
        WHY NO THRESHOLD:
        - Summary queries need broad context
        - Even "less relevant" chunks provide context
        - AutoMerging combines children back into parents
        """
        if self.vector_index is None:
            raise ValueError("Index not built. Call build_indexes() first.")
        
        # Create base vector retriever
        # WHY: Retrieves based on similarity
        # CRITICAL: Uses the embedding from vector_index (consistency!)
        base_retriever = VectorIndexRetriever(
            index=self.vector_index,
            similarity_top_k=top_k,
        )
        
        print(f"📚 Summary Retriever configured:")
        print(f"   Scope: Parent + Child chunks")
        print(f"   Top-k: {top_k}")
        print(f"   Similarity threshold: None (high recall)")
        print(f"   Uses embedding: {self.embedding_model}")
        
        return base_retriever
    
    def get_map_reduce_query_engine(
        self,
        top_k: int = 15,
    ):
        """
        Get MapReduce Query Engine for comprehensive summarization.
        
        WHY MAP-REDUCE:
        - Hierarchical summarization (map → reduce → final)
        - Can handle large amounts of context (50+ chunks)
        - Better quality for comprehensive claim summaries
        - Processes chunks systematically
        
        HOW IT WORKS:
        1. RETRIEVE: Get top_k relevant chunks via vector similarity
        2. MAP: Summarize each chunk individually (parallel)
        3. REDUCE: Recursively combine summaries (hierarchical)
        4. FINAL: Produce comprehensive summary
        
        Args:
            top_k: Number of chunks to retrieve (default 15 for comprehensive coverage)
        
        Returns:
            RetrieverQueryEngine configured with tree_summarize (MapReduce)
            
        WHY MORE CHUNKS (15 vs 8):
        - MapReduce can handle more chunks efficiently
        - Hierarchical combination prevents context overload
        - Better coverage for full-claim summarization
        
        WHY tree_summarize MODE:
        - LlamaIndex's implementation of MapReduce
        - Automatic batching and hierarchical reduction
        - Optimal for comprehensive summarization
        """
        if self.vector_index is None:
            raise ValueError("Index not built. Call build_indexes() first.")
        
        # Get THE SINGLE LLM instance
        llm = self._get_or_create_llm()
        
        # Create retriever for MapReduce
        # WHY: Same vector similarity, but retrieve more chunks
        retriever = VectorIndexRetriever(
            index=self.vector_index,
            similarity_top_k=top_k,
        )
        
        # Create MapReduce response synthesizer
        # WHY: tree_summarize = hierarchical MapReduce
        # HOW: Chunks → Individual summaries → Hierarchical merging → Final summary
        response_synthesizer = get_response_synthesizer(
            response_mode=ResponseMode.TREE_SUMMARIZE,
            llm=llm,
            verbose=True,  # Show MAP and REDUCE steps in console
        )
        
        # Create query engine combining retriever + MapReduce synthesizer
        # WHY: Query engine orchestrates retrieval + synthesis
        query_engine = RetrieverQueryEngine(
            retriever=retriever,
            response_synthesizer=response_synthesizer,
        )
        
        print(f"🗺️  MapReduce Query Engine configured:")
        print(f"   Mode: TREE_SUMMARIZE (hierarchical MapReduce)")
        print(f"   Top-k: {top_k} chunks")
        print(f"   LLM: {self.llm_model}")
        print(f"   Temperature: {self.llm_temperature}")
        print(f"   Uses embedding: {self.embedding_model}")
        print(f"   Process: Retrieve → Map → Reduce → Final Summary")
        
        return query_engine
    
    def query_needle(
        self,
        query: str,
        top_k: int = 5,
        similarity_threshold: float = 0.7,
    ) -> List[BaseNode]:
        """
        Execute a needle query (high precision).
        
        WHY THIS METHOD:
        - Convenience method for testing
        - Filters for child chunks
        - Applies similarity threshold
        
        Args:
            query: Query string
            top_k: Number of results
            similarity_threshold: Minimum similarity
            
        Returns:
            List of child chunk nodes above threshold
        """
        if self.vector_index is None:
            raise ValueError("Index not built. Call build_indexes() first.")
        
        # Get retriever
        retriever = self.get_needle_retriever(
            top_k=top_k,
            similarity_threshold=similarity_threshold
        )
        
        # Retrieve
        results = retriever.retrieve(query)
        
        # Filter for child chunks only
        # WHY: Needle queries need atomic facts
        child_results = [
            r for r in results 
            if r.node.metadata.get('chunk_level') == 'child'
            and r.score is not None
            and r.score >= similarity_threshold
        ]
        
        return [r.node for r in child_results]
    
    def query_summary(
        self,
        query: str,
        top_k: int = 8,
    ) -> List[BaseNode]:
        """
        Execute a summary query (high recall).
        
        WHY THIS METHOD:
        - Convenience method for testing
        - No filtering or thresholding
        - Returns diverse results
        
        Args:
            query: Query string
            top_k: Number of results
            
        Returns:
            List of nodes (parent + child)
        """
        if self.vector_index is None:
            raise ValueError("Index not built. Call build_indexes() first.")
        
        # Get retriever
        retriever = self.get_summary_retriever(top_k=top_k)
        
        # Retrieve
        results = retriever.retrieve(query)
        
        return [r.node for r in results]
    
    def save(self, persist_dir: str) -> None:
        """
        Save indexes and metadata to disk.
        
        WHY THIS METHOD:
        - Production systems need persistence
        - Avoids rebuilding indexes on restart
        - Enables index versioning
        
        Args:
            persist_dir: Directory to save indexes
            
        CRITICAL:
        - Saves StorageContext (includes embedding config)
        - Saves vector index
        - Saves metadata
        - Loading will restore the SAME embedding setup
        """
        if self.vector_index is None or self.storage_context is None:
            raise ValueError("No index to save. Call build_indexes() first.")
        
        persist_path = Path(persist_dir)
        persist_path.mkdir(parents=True, exist_ok=True)
        
        # Save vector index
        # WHY: Persists FAISS index + metadata
        self.storage_context.persist(persist_dir=str(persist_path))
        
        # Save claim metadata
        # WHY: Need to know which claim this index belongs to
        metadata = {
            "claim_id": self.claim_id,
            "claim_number": self.claim_number,
            "embedding_model": self.embedding_model,
            "vector_dimension": self.vector_dimension,
        }
        
        metadata_path = persist_path / "index_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"✅ Saved indexes to: {persist_dir}")
        print(f"   Claim #{self.claim_number}")
        print(f"   Embedding: {self.embedding_model}")
    
    @classmethod
    def load(cls, persist_dir: str) -> 'IndexLayer':
        """
        Load indexes from disk.
        
        WHY THIS METHOD:
        - Restores saved indexes
        - Recreates the SAME embedding configuration
        - Ready for querying immediately
        
        Args:
            persist_dir: Directory containing saved indexes
            
        Returns:
            IndexLayer instance with loaded indexes
            
        CRITICAL:
        - Recreates the SAME embedding model
        - Loads StorageContext (contains FAISS)
        - Maintains embedding consistency
        """
        persist_path = Path(persist_dir)
        
        if not persist_path.exists():
            raise ValueError(f"Index directory not found: {persist_dir}")
        
        # Load metadata
        metadata_path = persist_path / "index_metadata.json"
        if not metadata_path.exists():
            raise ValueError(f"Index metadata not found: {metadata_path}")
        
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        
        # Create instance with SAME embedding configuration
        # WHY: Ensures embedding consistency
        instance = cls(
            embedding_model=metadata['embedding_model'],
            vector_dimension=metadata['vector_dimension'],
        )
        
        instance.claim_id = metadata['claim_id']
        instance.claim_number = metadata['claim_number']
        
        # Recreate THE SINGLE embedding instance
        # WHY: Must match the embedding used during indexing
        embed_model = instance._get_or_create_embedding()
        
        # Load FAISS vector store from disk
        # WHY: FAISS data was persisted and needs to be loaded properly
        # CRITICAL: This loads the actual vectors, not just an empty index
        vector_store = FaissVectorStore.from_persist_dir(persist_dir=str(persist_path))
        
        # Load storage context with the loaded FAISS vector store
        # WHY: Connects all components together
        instance.storage_context = StorageContext.from_defaults(
            vector_store=vector_store,
            persist_dir=str(persist_path),
        )
        
        # Load vector index
        # WHY: Reconstructs the VectorStoreIndex from persisted data
        # CRITICAL: Pass embed_model to ensure consistency
        loaded_index = load_index_from_storage(
            storage_context=instance.storage_context,
            embed_model=embed_model,  # THE SINGLE EMBEDDING (must match!)
        )
        
        # Cast to VectorStoreIndex
        # WHY: load_index_from_storage returns BaseIndex, but we know it's VectorStoreIndex
        if not isinstance(loaded_index, VectorStoreIndex):
            raise TypeError(f"Expected VectorStoreIndex, got {type(loaded_index)}")
        
        instance.vector_index = loaded_index
        
        print(f"✅ Loaded indexes from: {persist_dir}")
        print(f"   Claim #{instance.claim_number}")
        print(f"   Embedding: {instance.embedding_model}")
        
        return instance


# Production-ready factory function
def create_index_layer(
    embedding_model: str = "text-embedding-3-small",
    vector_dimension: int = 1536,
) -> IndexLayer:
    """
    Factory function to create an index layer.
    
    WHY: Provides clean interface for importing and using this layer.
    
    Args:
        embedding_model: OpenAI embedding model name
        vector_dimension: Embedding dimension
        
    Returns:
        Configured IndexLayer instance
    """
    return IndexLayer(
        embedding_model=embedding_model,
        vector_dimension=vector_dimension,
    )


class ClaimIndexManager:
    """
    High-level manager that orchestrates the complete pipeline from PDF to retrievers.
    
    This class provides a simplified interface for quick-start scripts by:
    - Orchestrating PDF Ingestion → Segmentation → Chunking → Indexing
    - Handling multi-claim PDFs (processes first claim only for simplicity)
    - Providing simple build_index(pdf_path) and load_index(persist_dir) methods
    - Exposing retrievers for use with agents
    
    WHY THIS EXISTS:
    - Simplifies setup in demo/quickstart scripts
    - Hides complexity of the multi-layer pipeline
    - Provides backward compatibility with older API
    """
    
    def __init__(
        self,
        embedding_model: str = "text-embedding-3-small",
        vector_dimension: int = 1536,
    ):
        """
        Initialize the claim index manager.
        
        Args:
            embedding_model: OpenAI embedding model name
            vector_dimension: Embedding dimension
        """
        self.embedding_model = embedding_model
        self.vector_dimension = vector_dimension
        self.index_layer: Optional[IndexLayer] = None
    
    def build_index(
        self,
        pdf_path: str,
        persist_dir: str = "storage",
        claim_index: int = 0,
        index_all_claims: bool = False,
    ) -> None:
        """
        Build index from a PDF file (complete pipeline).
        
        This method orchestrates the entire pipeline:
        1. PDF Ingestion: PDF → Document
        2. Claim Segmentation: Document → List[Claim Documents]
        3. Chunking: Claim Document(s) → Hierarchical Nodes
        4. Indexing: Nodes → VectorStoreIndex + Retrievers
        5. Persistence: Save to disk
        
        Args:
            pdf_path: Path to PDF file
            persist_dir: Directory to save indexes
            claim_index: Which claim to process (default: 0, first claim)
                        Ignored if index_all_claims=True
            index_all_claims: If True, indexes ALL claims in the PDF (default: False)
        
        WHY THIS METHOD:
        - One-line setup for demos and quickstarts
        - Handles the full pipeline complexity
        - Automatically persists for later use
        - Can index single claim or all claims
        """
        # Import pipeline components
        # WHY: Import here to avoid circular dependencies
        from RAG.PDF_Ingestion import create_ingestion_pipeline
        from RAG.Claim_Segmentation import create_claim_segmentation_pipeline
        from RAG.Chunking_Layer import create_chunking_pipeline
        
        print(f"🚀 Building index from PDF: {pdf_path}")
        print(f"   This orchestrates the full pipeline...")
        
        # Stage 1: PDF Ingestion
        print(f"\n[1/5] PDF Ingestion...")
        ingestion_pipeline = create_ingestion_pipeline(document_type="insurance_claim_form")
        document = ingestion_pipeline.ingest(pdf_path)
        print(f"✅ Ingested PDF: {document.metadata.get('filename', 'unknown')}")
        
        # Stage 2: Claim Segmentation
        print(f"\n[2/5] Claim Segmentation...")
        segmentation_pipeline = create_claim_segmentation_pipeline()
        claim_documents = segmentation_pipeline.split_into_claims(document)
        print(f"✅ Found {len(claim_documents)} claims")
        
        # Determine which claims to process
        if index_all_claims:
            print(f"   📋 Processing ALL {len(claim_documents)} claims")
            claims_to_process = claim_documents
        else:
            # Select single claim to index
            if claim_index >= len(claim_documents):
                raise ValueError(
                    f"Claim index {claim_index} out of range. "
                    f"PDF has {len(claim_documents)} claims (0-{len(claim_documents)-1})"
                )
            selected_claim = claim_documents[claim_index]
            claim_number = selected_claim.metadata.get('claim_number', 'unknown')
            print(f"   Processing Claim #{claim_number} (index {claim_index})")
            claims_to_process = [selected_claim]
        
        # Stage 3: Chunking (all selected claims)
        print(f"\n[3/5] Chunking into hierarchical nodes...")
        chunking_pipeline = create_chunking_pipeline(
            parent_chunk_size=400,
            child_chunk_size=120,
        )
        
        all_nodes = []
        for claim in claims_to_process:
            claim_num = claim.metadata.get('claim_number', 'unknown')
            nodes = chunking_pipeline.build_nodes(claim)
            all_nodes.extend(nodes)
            if index_all_claims:
                print(f"   ✓ Claim #{claim_num}: {len(nodes)} nodes")
        
        print(f"✅ Created {len(all_nodes)} total hierarchical nodes")
        
        # Stage 4: Indexing (all nodes together)
        print(f"\n[4/5] Building vector indexes...")
        self.index_layer = IndexLayer(
            embedding_model=self.embedding_model,
            vector_dimension=self.vector_dimension,
        )
        
        # Set metadata for multi-claim index
        if index_all_claims:
            claim_id = "all_claims"
            claim_number = f"ALL_{len(claim_documents)}_CLAIMS"
        else:
            claim_id = claims_to_process[0].metadata.get('claim_id')
            claim_number = claims_to_process[0].metadata.get('claim_number', 'unknown')
        
        self.index_layer.build_indexes(
            nodes=all_nodes,
            claim_id=claim_id,
            claim_number=claim_number,
        )
        print(f"✅ Indexes built")
        
        # Stage 5: Persistence
        print(f"\n[5/5] Saving to disk...")
        self.index_layer.save(persist_dir=persist_dir)
        print(f"✅ Saved to {persist_dir}")
        
        if index_all_claims:
            print(f"\n✅ Complete! Indexed ALL {len(claim_documents)} claims. Ready for querying any claimant!")
        else:
            print(f"\n✅ Complete! Index ready for querying.")
    
    def load_index(self, persist_dir: str = "storage") -> None:
        """
        Load index from disk.
        
        Args:
            persist_dir: Directory containing saved indexes
        
        WHY THIS METHOD:
        - Fast startup without rebuilding
        - Restores complete index state
        """
        print(f"📂 Loading index from: {persist_dir}")
        self.index_layer = IndexLayer.load(persist_dir=persist_dir)
        print(f"✅ Index loaded and ready")
    
    def get_needle_retriever(self, top_k: int = 5, similarity_threshold: float = 0.7):
        """
        Get Needle Retriever (high precision, child chunks only).
        
        Args:
            top_k: Number of chunks to retrieve
            similarity_threshold: Minimum similarity score
            
        Returns:
            Configured retriever for needle queries
        """
        if self.index_layer is None:
            raise ValueError("Index not loaded. Call build_index() or load_index() first.")
        
        return self.index_layer.get_needle_retriever(
            top_k=top_k,
            similarity_threshold=similarity_threshold
        )
    
    def get_summary_retriever(self, top_k: int = 8):
        """
        Get Summary Retriever (high recall, parent + child chunks).
        
        Args:
            top_k: Number of chunks to retrieve
            
        Returns:
            Configured retriever for summary queries
        """
        if self.index_layer is None:
            raise ValueError("Index not loaded. Call build_index() or load_index() first.")
        
        return self.index_layer.get_summary_retriever(top_k=top_k)
    
    def get_map_reduce_query_engine(self, top_k: int = 15):
        """
        Get MapReduce Query Engine for comprehensive summarization.
        
        WHY MAP-REDUCE:
        - Better for comprehensive claim summarization
        - Hierarchical summarization (map → reduce → final)
        - Can handle more chunks (15+ vs 8)
        - Systematic processing of all relevant context
        
        Args:
            top_k: Number of chunks to retrieve (default 15 for comprehensive coverage)
            
        Returns:
            RetrieverQueryEngine configured with tree_summarize (MapReduce)
        """
        if self.index_layer is None:
            raise ValueError("Index not loaded. Call build_index() or load_index() first.")
        
        return self.index_layer.get_map_reduce_query_engine(top_k=top_k)

