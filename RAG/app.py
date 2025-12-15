"""
====================================================
RAG APPLICATION - PRODUCTION ENTRY POINT
====================================================

RESPONSIBILITY:
This is the FINAL APPLICATION ENTRY POINT.
It connects ALL existing layers into ONE pipeline.

This is GLUE CODE ONLY.
NO re-implementation.
NO new logic.
ONLY orchestration.

PIPELINE:
PDF → Ingestion → Segmentation → Chunking → Indexing → Agents → Answer

FRAMEWORKS:
- LlamaIndex: PDF, Segmentation, Chunking, Indexing
- LangChain: Router, Needle, Summary, Orchestrator

CRITICAL:
- ONE embedding instance (created in IndexLayer)
- SAME embedding used for indexing and querying
- NO embedding creation here
====================================================
"""

from typing import Dict, Any, Optional, List
from pathlib import Path

# LlamaIndex components (data processing)
from llama_index.core import Document
from llama_index.core.schema import BaseNode

# Import existing layers
from RAG.PDF_Ingestion import create_ingestion_pipeline, PDFIngestionPipeline
from RAG.Claim_Segmentation import create_claim_segmentation_pipeline, ClaimSegmentationPipeline
from RAG.Chunking_Layer import create_chunking_pipeline, ChunkingPipeline
from RAG.Index_Layer import IndexLayer, create_index_layer

# LangChain components (agents)
from RAG.Agents import RouterAgent, NeedleAgent, SummaryAgent
from RAG.Orchestration import Orchestrator


class RAGApplication:
    """
    Production-grade RAG application entry point.
    
    Connects all layers into a single executable pipeline:
    PDF → Ingestion → Segmentation → Chunking → Indexing → Agents → Answer
    
    WHY THIS EXISTS:
    - Single entry point for external consumers
    - Orchestrates all layers in correct order
    - Enforces embedding consistency
    - Provides clean public API
    
    WHY NO INTERNAL LOGIC:
    - All intelligence lives in specialized layers
    - This is GLUE CODE only
    - Maintains separation of concerns
    """
    
    def __init__(
        self,
        embedding_model: str = "text-embedding-3-small",
        llm_model: str = "gpt-4o-mini",
    ):
        """
        Initialize the RAG application.
        
        Args:
            embedding_model: OpenAI embedding model for indexing/retrieval
            llm_model: OpenAI LLM model for agents
        
        WHY THESE PARAMS:
        - embedding_model: Used by IndexLayer (consistency critical)
        - llm_model: Used by all agents (Router, Needle, Summary)
        """
        self.embedding_model = embedding_model
        self.llm_model = llm_model
        
        print("="*70)
        print("🚀 RAG APPLICATION INITIALIZED")
        print("="*70)
        print(f"Embedding Model: {embedding_model}")
        print(f"LLM Model: {llm_model}")
        print("="*70)
    
    def run(
        self,
        pdf_path: str,
        question: str,
        claim_id: Optional[str] = None,
        index_all_claims: bool = True,
    ) -> Dict[str, Any]:
        """
        Execute the complete RAG pipeline.
        
        Pipeline:
        1. PDF Ingestion → Document
        2. Claim Segmentation → List[Claim Documents]
        3. Claim Selection → Selected claim(s)
        4. Chunking → Hierarchical nodes
        5. Indexing → Vector store + Retrievers
        6. Agent Initialization → Router, Needle, Summary
        7. Orchestration → Route + Execute
        8. Return → Structured answer
        
        Args:
            pdf_path: Path to PDF file
            question: User's question
            claim_id: Optional claim ID to query specific claim
            index_all_claims: If True, indexes ALL claims (default: True)
        
        Returns:
            Dictionary with:
                - claim_id: str
                - route: "needle" | "summary"
                - answer: str | None
                - confidence: float
                - sources: List[str]
                - reason: str
        
        WHY THIS METHOD:
        - Single public API for external consumers
        - Orchestrates entire pipeline
        - Returns consistent format
        """
        print("\n" + "="*70)
        print("🎬 STARTING FULL RAG PIPELINE")
        print("="*70)
        print(f"PDF: {Path(pdf_path).name}")
        print(f"Question: {question}")
        if claim_id:
            print(f"Claim ID: {claim_id}")
        print("="*70)
        
        # ============================================================
        # STEP 1: PDF INGESTION
        # ============================================================
        # WHY: Convert PDF bytes to LlamaIndex Document
        # WHO: PDFIngestionPipeline (LlamaIndex)
        # WHAT: Returns clean Document with metadata
        
        print("\n[1/7] 📄 PDF INGESTION...")
        ingestion_pipeline = create_ingestion_pipeline(
            document_type="insurance_claim_form"
        )
        document = ingestion_pipeline.ingest(pdf_path)
        print(f"✅ Ingested: {document.metadata.get('filename', 'unknown')}")
        
        # ============================================================
        # STEP 2: CLAIM SEGMENTATION
        # ============================================================
        # WHY: Split multi-claim PDF into individual claims
        # WHO: ClaimSegmentationPipeline (LlamaIndex)
        # WHAT: Returns List[Document], one per claim
        
        print("\n[2/7] ✂️  CLAIM SEGMENTATION...")
        segmentation_pipeline = create_claim_segmentation_pipeline()
        claim_documents = segmentation_pipeline.split_into_claims(document)
        print(f"✅ Found {len(claim_documents)} claims")
        
        # Error check: No claims
        if not claim_documents:
            raise ValueError("PDF contains no claims")
        
        # ============================================================
        # STEP 3: CLAIM SELECTION
        # ============================================================
        # WHY: Determine which claim(s) to index
        # LOGIC:
        #   - If index_all_claims=True: process ALL claims (recommended)
        #   - Else if claim_id provided: select matching claim
        #   - Else: use first claim only
        
        print("\n[3/7] 🎯 CLAIM SELECTION...")
        if index_all_claims:
            # Index ALL claims (enables questions about any claimant)
            claims_to_process = claim_documents
            print(f"✅ Selected ALL {len(claim_documents)} claims")
            print(f"   You can ask about ANY claimant!")
        elif claim_id:
            # Find matching claim
            selected_claim = None
            for claim_doc in claim_documents:
                if claim_doc.metadata.get('claim_id') == claim_id:
                    selected_claim = claim_doc
                    break
            
            if selected_claim is None:
                raise ValueError(f"Claim ID '{claim_id}' not found in PDF")
            
            claim_number = selected_claim.metadata.get('claim_number', 'unknown')
            print(f"✅ Selected Claim #{claim_number} (ID: {claim_id})")
            claims_to_process = [selected_claim]
        else:
            # Use first claim
            selected_claim = claim_documents[0]
            claim_id = selected_claim.metadata.get('claim_id', 'unknown')
            claim_number = selected_claim.metadata.get('claim_number', 'unknown')
            print(f"✅ Selected Claim #{claim_number} (default: first claim)")
            claims_to_process = [selected_claim]
        
        # ============================================================
        # STEP 4: CHUNKING
        # ============================================================
        # WHY: Convert Document(s) to hierarchical nodes
        # WHO: ChunkingPipeline (LlamaIndex)
        # WHAT: Returns List[BaseNode] (Section → Parent → Child)
        
        print("\n[4/7] 🔪 CHUNKING...")
        chunking_pipeline = create_chunking_pipeline(
            parent_chunk_size=400,
            child_chunk_size=120,
        )
        
        # Process all selected claims
        all_nodes = []
        for claim_doc in claims_to_process:
            claim_num = claim_doc.metadata.get('claim_number', 'unknown')
            nodes = chunking_pipeline.build_nodes(claim_doc)
            all_nodes.extend(nodes)
            if len(claims_to_process) > 1:
                print(f"   ✓ Claim #{claim_num}: {len(nodes)} nodes")
        
        print(f"✅ Created {len(all_nodes)} total hierarchical nodes")
        
        # ============================================================
        # STEP 5: INDEX LAYER
        # ============================================================
        # WHY: Build vector indexes and retrievers
        # WHO: IndexLayer (LlamaIndex)
        # WHAT: Creates embeddings, FAISS index, retrievers
        # CRITICAL: ONE embedding instance created here
        
        print("\n[5/7] 📚 INDEX LAYER...")
        index_layer = create_index_layer(
            embedding_model=self.embedding_model,
            vector_dimension=1536,
        )
        
        # Set metadata for indexing
        if len(claims_to_process) > 1:
            # Multi-claim index
            claim_id = "all_claims"
            claim_number = f"ALL_{len(claims_to_process)}_CLAIMS"
        else:
            # Single claim
            claim_id = claims_to_process[0].metadata.get('claim_id', 'unknown')
            claim_number = claims_to_process[0].metadata.get('claim_number', 'unknown')
        
        # Build indexes (creates THE SINGLE embedding instance)
        index_layer.build_indexes(
            nodes=all_nodes,
            claim_id=claim_id,
            claim_number=claim_number,
        )
        
        # Get retrievers (use SAME embedding via index_layer)
        needle_retriever = index_layer.get_needle_retriever(
            top_k=5,
            similarity_threshold=0.7,
        )
        summary_retriever = index_layer.get_summary_retriever(
            top_k=8,
        )
        
        print(f"✅ Indexes built")
        print(f"✅ Retrievers created (embedding: {self.embedding_model})")
        
        # ============================================================
        # STEP 6: AGENT INITIALIZATION
        # ============================================================
        # WHY: Create agents for routing and answering
        # WHO: RouterAgent, NeedleAgent, SummaryAgent (LangChain)
        # WHAT: Initialize with LLM configuration
        
        print("\n[6/7] 🤖 AGENT INITIALIZATION...")
        router_agent = RouterAgent(
            model=self.llm_model,
            temperature=0.0,
        )
        needle_agent = NeedleAgent(
            model=self.llm_model,
            temperature=0.0,
        )
        summary_agent = SummaryAgent(
            model=self.llm_model,
            temperature=0.2,
        )
        print(f"✅ Agents initialized (LLM: {self.llm_model})")
        
        # ============================================================
        # STEP 7: ORCHESTRATION
        # ============================================================
        # WHY: Coordinate routing and execution
        # WHO: Orchestrator (LangChain)
        # WHAT: Routes question, executes agent, returns answer
        
        print("\n[7/7] 🎭 ORCHESTRATION...")
        orchestrator = Orchestrator(
            router_agent=router_agent,
            needle_agent=needle_agent,
            summary_agent=summary_agent,
            needle_retriever=needle_retriever,
            summary_retriever=summary_retriever,
        )
        
        # Execute pipeline
        result = orchestrator.run(question=question, claim_id=claim_id)
        
        # ============================================================
        # RETURN
        # ============================================================
        # WHY: Provide structured response
        # FORMAT: Consistent interface for consumers
        
        print("\n" + "="*70)
        print("✅ PIPELINE COMPLETE")
        print("="*70)
        
        return {
            "claim_id": claim_id,
            "route": result["route"],
            "answer": result["answer"],
            "confidence": result["confidence"],
            "sources": result["sources"],
            "reason": result["reason"],
        }


# ====================================================
# FACTORY FUNCTION
# ====================================================

def create_rag_application(
    embedding_model: str = "text-embedding-3-small",
    llm_model: str = "gpt-4o-mini",
) -> RAGApplication:
    """
    Factory function to create RAG application.
    
    WHY: Clean interface for creating application.
    
    Args:
        embedding_model: OpenAI embedding model
        llm_model: OpenAI LLM model
    
    Returns:
        Configured RAGApplication instance
    """
    return RAGApplication(
        embedding_model=embedding_model,
        llm_model=llm_model,
    )

