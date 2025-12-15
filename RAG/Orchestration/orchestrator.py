"""
====================================================
ORCHESTRATOR - MULTI-AGENT COORDINATION
====================================================

RESPONSIBILITY:
This orchestrator coordinates the RAG pipeline.
It does NOT retrieve data.
It does NOT generate answers.
It ONLY routes questions and delegates to agents.

WHY THIS EXISTS:
- Multi-agent systems need coordination
- Routing logic should be separate from execution
- Consistent interface for external consumers
- Single entry point for RAG pipeline

WHY LANGCHAIN:
- LangChain provides orchestration patterns
- Clean dependency injection
- Explicit, readable flow

WHY NO RETRIEVAL HERE:
- Orchestrator doesn't touch data
- Retrievers are injected from Index Layer
- Agents handle retrieval interaction
- Clear separation of concerns

CRITICAL RULES:
- NEVER access FAISS
- NEVER build retrievers
- NEVER create embeddings
- NEVER implement fallback logic
- ONLY coordinate existing agents

====================================================
"""

from typing import Dict, Any, Optional, List
import re
from llama_index.core.vector_stores import MetadataFilters, ExactMatchFilter
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.schema import NodeWithScore


# ====================================================
# POST-FILTER RETRIEVER - FAISS doesn't support metadata filtering
# ====================================================

class PostFilterRetriever:
    """
    Wrapper around VectorIndexRetriever that applies metadata filtering
    AFTER retrieval (post-filtering).
    
    WHY THIS EXISTS:
    - FAISS vector store doesn't support native metadata filtering
    - Solution: Retrieve MORE results, then filter in Python
    - Trade-off: Less efficient but works with FAISS
    
    HOW IT WORKS:
    1. Retrieve top_k * 3 results from FAISS
    2. Filter by claim_number OR claimant_name metadata (DYNAMIC!)
    3. Return top_k filtered results
    """
    
    def __init__(
        self, 
        base_retriever, 
        claim_number: Optional[str] = None, 
        claimant_name: Optional[str] = None,
        original_top_k: int = 5
    ):
        """
        Args:
            base_retriever: Original VectorIndexRetriever
            claim_number: Claim number to filter for (e.g., "5")
            claimant_name: Claimant name to filter for (e.g., "Jon Mor")
            original_top_k: Desired number of results after filtering
        """
        self.base_retriever = base_retriever
        self.claim_number = claim_number
        self.claimant_name = claimant_name
        self.original_top_k = original_top_k
        # Retrieve 10x more to account for filtering + auto-merging expansion
        # WHY: Auto-merging can expand results, so we need more initial chunks
        self.expanded_top_k = original_top_k * 10
        
        if not claim_number and not claimant_name:
            raise ValueError("Must provide either claim_number or claimant_name")
    
    def retrieve(self, query_str: str) -> List[NodeWithScore]:
        """
        Retrieve and filter results by claim_number OR claimant_name.
        
        WHY EXPANDED RETRIEVAL:
        - If we retrieve 5 results and all are from wrong claims, we get 0 results
        - By retrieving more results, we're more likely to find results from the right claim
        - Trade-off: More computation but better recall
        """
        # Step 1: Get the underlying index
        # Handle both AutoMergingRetriever and VectorIndexRetriever
        if hasattr(self.base_retriever, '_vector_retriever'):
            # AutoMergingRetriever case
            vector_index = self.base_retriever._vector_retriever._index
        elif hasattr(self.base_retriever, '_index'):
            # VectorIndexRetriever case
            vector_index = self.base_retriever._index
        else:
            raise ValueError("Cannot access index from base_retriever")
        
        # Step 2: Retrieve expanded results from FAISS
        # Create a temporary retriever with expanded top_k
        expanded_retriever = VectorIndexRetriever(
            index=vector_index,
            similarity_top_k=self.expanded_top_k,
        )
        
        all_results = expanded_retriever.retrieve(query_str)
        
        # Step 2: Filter by claim_number OR claimant_name metadata (DYNAMIC!)
        filtered_results = []
        for node_with_score in all_results:
            metadata = node_with_score.node.metadata
            
            # Match if claim_number matches (if provided)
            if self.claim_number and metadata.get("claim_number") == self.claim_number:
                filtered_results.append(node_with_score)
                continue
            
            # Match if claimant_name matches (if provided)
            if self.claimant_name and metadata.get("claimant_name") == self.claimant_name:
                filtered_results.append(node_with_score)
                continue
        
        # Step 3: Return top_k filtered results
        return filtered_results[:self.original_top_k]
    
    # Expose _index for compatibility
    @property
    def _index(self):
        # Handle both AutoMergingRetriever and VectorIndexRetriever
        if hasattr(self.base_retriever, '_vector_retriever'):
            return self.base_retriever._vector_retriever._index
        elif hasattr(self.base_retriever, '_index'):
            return self.base_retriever._index
        else:
            raise ValueError("Cannot access index from base_retriever")
    
    @property
    def _similarity_top_k(self):
        return self.original_top_k


# ====================================================
# QUERY PREPROCESSOR - Extract Claim Numbers
# ====================================================

def extract_claimant_name(query: str) -> Optional[str]:
    """
    Extract claimant name from user query DYNAMICALLY (no hardcoding!).
    
    WHY: Questions like "What is Jon Mor's phone?" should filter to Jon Mor's claim.
    
    Strategy:
    - Look for capitalized names in query
    - Stop at common field names (Date, Incident, etc.) to avoid false matches
    - Return the name for metadata filtering
    
    Returns: Claimant name as string or None if not found
    """
    # Pattern: Look for capitalized first and last name
    # Matches: "Jon Mor", "Sarah Klein", "David Ross", etc.
    # Stop words that indicate we've gone past the name into other fields
    stop_words = ['Date', 'Incident', 'Repair', 'Appointment', 'Account', 'Number', 
                  'Phone', 'Email', 'Address', 'Location', 'Vehicle', 'VIN', 
                  'License', 'Plate', 'Make', 'Model', 'Year', 'Claim']
    
    # Find all potential names (sequences of capitalized words)
    # Pattern: 2-3 capitalized words (e.g., "Jon Mor", "Sarah Klein", "Lior Avraham")
    pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\b'
    matches = re.finditer(pattern, query)
    
    for match in matches:
        potential_name = match.group(1).strip()
        # Check if any word in the name is a stop word
        name_words = potential_name.split()
        if not any(word in stop_words for word in name_words):
            # Found a valid name (doesn't contain stop words)
            return potential_name
    
    return None


def extract_claim_number(query: str) -> Optional[str]:
    """
    Extract claim number from user query.
    
    Patterns matched:
    - "claim number 5", "claim #5", "form #5"
    - "AUTO CLAIM FORM #5"
    
    Returns claim number as string (e.g., "5") or None.
    
    NOTE: This does NOT handle claimant names. Use extract_claimant_name() for that.
    """
    # Pattern 1: "claim number X"
    match = re.search(r'claim\s+number\s+(\d+)', query, re.IGNORECASE)
    if match:
        return match.group(1)
    
    # Pattern 2: "claim #X"
    match = re.search(r'claim\s+#(\d+)', query, re.IGNORECASE)
    if match:
        return match.group(1)
    
    # Pattern 3: "form #X"
    match = re.search(r'form\s+#(\d+)', query, re.IGNORECASE)
    if match:
        return match.group(1)
    
    # Pattern 4: "form number X"
    match = re.search(r'form\s+number\s+(\d+)', query, re.IGNORECASE)
    if match:
        return match.group(1)
    
    return None


def create_claim_filter(claim_number: Optional[str] = None, claimant_name: Optional[str] = None) -> MetadataFilters:
    """
    Create metadata filter for claim matching (by number OR name).
    
    WHY: Ensures retrieval ONLY returns chunks from specified claim.
    
    Args:
        claim_number: Claim number to filter by (e.g., "5")
        claimant_name: Claimant name to filter by (e.g., "Jon Mor")
    
    Returns:
        MetadataFilters for exact matching
    """
    filters = []
    
    if claim_number:
        filters.append(ExactMatchFilter(
            key="claim_number",
            value=claim_number
        ))
    
    if claimant_name:
        filters.append(ExactMatchFilter(
            key="claimant_name",
            value=claimant_name
        ))
    
    if not filters:
        raise ValueError("Must provide either claim_number or claimant_name")
    
    return MetadataFilters(filters=filters)


# ====================================================
# ORCHESTRATOR - Pipeline Coordinator
# ====================================================

class Orchestrator:
    """
    Production-grade RAG pipeline orchestrator.
    
    Coordinates multi-agent flow:
    1. Route question (Router Agent)
    2. Execute with appropriate agent (Needle or Summary)
    3. Return unified response
    
    WHY THIS CLASS:
    - Single entry point for RAG system
    - Coordinates multiple agents
    - Ensures consistent response format
    - Simplifies external integration
    
    WHY DEPENDENCY INJECTION:
    - Agents are created externally
    - Retrievers are provided by Index Layer
    - Orchestrator has zero business logic
    - Easy to test with mocks
    - Flexible configuration
    
    ARCHITECTURE:
    - All dependencies injected via constructor
    - Simple linear flow (no branching logic)
    - No state between calls (stateless)
    - No retries or fallbacks
    """
    
    def __init__(
        self,
        router_agent,
        needle_agent,
        summary_agent,
        needle_retriever,
        summary_retriever=None,
        map_reduce_query_engine=None,
    ):
        """
        Initialize the Orchestrator with all dependencies.
        
        Args:
            router_agent: RouterAgent instance (classifies questions)
            needle_agent: NeedleAgent instance (atomic fact extraction)
            summary_agent: SummaryAgent instance (contextual synthesis)
            needle_retriever: Retriever for needle questions (from Index Layer)
            summary_retriever: Retriever for summary questions (legacy, optional)
            map_reduce_query_engine: MapReduce QueryEngine for summary questions (recommended)
        
        WHY ALL DEPENDENCIES INJECTED:
        - Orchestrator has ZERO creation logic
        - Each component can be configured independently
        - Easy to swap implementations
        - Easy to test with mocks
        - No hidden dependencies
        
        WHY MAP-REDUCE PREFERRED:
        - Better for comprehensive summaries
        - Hierarchical summarization (map → reduce)
        - Can handle more chunks efficiently
        - Falls back to simple retriever if not provided
        """
        # Store agents
        # WHY: Agents perform routing and answering
        self.router_agent = router_agent
        self.needle_agent = needle_agent
        self.summary_agent = summary_agent
        
        # Store retrievers/query engines
        # WHY: Retrievers are built by Index Layer with proper config
        self.needle_retriever = needle_retriever
        self.summary_retriever = summary_retriever
        self.map_reduce_query_engine = map_reduce_query_engine
        
        # Validate that we have at least one summary method
        if summary_retriever is None and map_reduce_query_engine is None:
            raise ValueError("Must provide either summary_retriever or map_reduce_query_engine")
        
        print(f"✅ Orchestrator initialized")
        print(f"   Router Agent: {type(router_agent).__name__}")
        print(f"   Needle Agent: {type(needle_agent).__name__}")
        print(f"   Summary Agent: {type(summary_agent).__name__}")
        print(f"   Needle Retriever: {type(needle_retriever).__name__}")
        if map_reduce_query_engine:
            print(f"   Summary Mode: MAP-REDUCE (tree_summarize)")
        else:
            print(f"   Summary Retriever: {type(summary_retriever).__name__}")
    
    def run(
        self,
        question: str,
        claim_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute the full RAG pipeline.
        
        This is the main public method of the Orchestrator.
        
        Pipeline:
        1. ROUTE: Classify question (needle vs summary)
        2. EXECUTE: Call appropriate agent with appropriate retriever
        3. RETURN: Unified response format
        
        Args:
            question: User's question string
            claim_id: Optional claim identifier (for future multi-claim support)
        
        Returns:
            Dictionary with unified response:
                - route: "needle" or "summary"
                - answer: str or None
                - confidence: float (0.0 to 1.0)
                - sources: list of chunk IDs
                - reason: str explanation
        
        WHY THIS METHOD:
        - Single entry point for RAG system
        - Clean, predictable interface
        - No side effects (stateless)
        - Consistent output format
        
        WHY NO FALLBACK LOGIC:
        - Routing should be reliable (Router Agent's job)
        - If agent fails, surface the error
        - No silent failures
        - Explicit behavior
        """
        if not question or not question.strip():
            raise ValueError("Question cannot be empty")
        
        print("\n" + "="*70)
        print("🚀 RAG PIPELINE STARTED")
        print("="*70)
        print(f"Question: {question}")
        if claim_id:
            print(f"Claim ID: {claim_id}")
        
        # ============================================================
        # STEP 0: QUERY PREPROCESSING - Extract claim identifiers
        # ============================================================
        # WHY: If user mentions specific claim (by number OR name), filter retrieval
        # WHY: "claim number 5" OR "Jon Mor's phone" should filter to that claim ONLY
        # WHY: Prevents semantic similarity from returning wrong claims
        
        claim_number = extract_claim_number(question)
        claimant_name = extract_claimant_name(question)
        
        # Determine which retrievers to use
        if claim_number or claimant_name:
            # Create post-filtered retrievers for this specific claim
            # WHY POST-FILTERING: FAISS doesn't support native metadata filtering
            if claim_number:
                print(f"\n🔍 Detected claim number: {claim_number}")
            if claimant_name:
                print(f"\n🔍 Detected claimant name: {claimant_name}")
            print("   Creating post-filtered retrievers...")
            
            # Get original top_k values
            needle_top_k = getattr(self.needle_retriever, '_similarity_top_k', 5)
            summary_top_k = getattr(self.summary_retriever, '_similarity_top_k', 8)
            
            # Create post-filter wrappers (filter by number OR name)
            needle_retriever_to_use = PostFilterRetriever(
                base_retriever=self.needle_retriever,
                claim_number=claim_number,
                claimant_name=claimant_name,
                original_top_k=needle_top_k
            )
            
            summary_retriever_to_use = PostFilterRetriever(
                base_retriever=self.summary_retriever,
                claim_number=claim_number,
                claimant_name=claimant_name,
                original_top_k=summary_top_k
            )
            
            if claim_number:
                print(f"   ✅ Will filter to claim_number = {claim_number}")
            if claimant_name:
                print(f"   ✅ Will filter to claimant_name = {claimant_name}")
        else:
            # Use default retrievers (no filtering)
            needle_retriever_to_use = self.needle_retriever
            summary_retriever_to_use = self.summary_retriever
        
        # ============================================================
        # STEP 1: ROUTING - Classify the question
        # ============================================================
        # WHY: Different question types need different strategies
        # WHY: Router Agent has the classification logic
        # WHY: Routing happens BEFORE retrieval (optimization)
        
        print("\n[STEP 1] ROUTING")
        print("─" * 70)
        
        route_decision = self.router_agent.route(question)
        
        route = route_decision["route"]
        route_confidence = route_decision["confidence"]
        route_reason = route_decision["reason"]
        
        print(f"✓ Route:      {route.upper()}")
        print(f"✓ Confidence: {route_confidence:.2f}")
        print(f"✓ Reason:     {route_reason}")
        
        # ============================================================
        # STEP 2: EXECUTION - Call appropriate agent
        # ============================================================
        # WHY: Each agent specializes in different question types
        # WHY: Each agent uses different retriever configuration
        # WHY: Agents handle all retrieval interaction
        
        print("\n[STEP 2] EXECUTION")
        print("─" * 70)
        
        if route == "needle":
            # NEEDLE PATH: Atomic fact extraction
            # WHY: Question needs ONE precise fact
            # WHY: Uses child chunks with high similarity threshold
            print("→ Executing NEEDLE AGENT...")
            
            agent_result = self.needle_agent.answer(
                question=question,
                retriever=needle_retriever_to_use  # Use filtered if claim number detected
            )
            
        elif route == "summary":
            # SUMMARY PATH: Contextual synthesis
            # WHY: Question needs multiple facts or explanation
            # WHY: Prefer MapReduce for comprehensive summarization
            print("→ Executing SUMMARY AGENT...")
            
            # Use MapReduce if available, otherwise fallback to retriever
            if self.map_reduce_query_engine is not None:
                print("   Using MAP-REDUCE (tree_summarize) for hierarchical summarization")
                agent_result = self.summary_agent.answer(
                    question=question,
                    query_engine=self.map_reduce_query_engine  # MapReduce for comprehensive summaries
                )
            else:
                print("   Using simple retrieval + synthesis")
                agent_result = self.summary_agent.answer(
                    question=question,
                    retriever=summary_retriever_to_use  # Use filtered if claim number detected
                )
            
        else:
            # This should never happen if Router Agent works correctly
            # WHY: Router Agent schema enforces "needle" or "summary"
            raise ValueError(f"Invalid route: {route}. Expected 'needle' or 'summary'.")
        
        # ============================================================
        # STEP 3: RESPONSE NORMALIZATION - Unify output format
        # ============================================================
        # WHY: External consumers need consistent interface
        # WHY: Attach routing metadata to agent result
        # WHY: No additional processing or logic
        
        print("\n[STEP 3] RESPONSE")
        print("─" * 70)
        
        # Build unified response
        # WHY: Combines routing decision + agent result
        # WHY: Standard format for all questions
        unified_response = {
            "route": route,                                              # Which agent was used
            "answer": agent_result["answer"],                            # Final answer
            "confidence": agent_result["confidence"],                     # Agent's confidence
            "sources": agent_result["sources"],                          # Chunk IDs used
            "retrieved_chunks_content": agent_result.get("retrieved_chunks_content", []),  # Actual chunk text (for evaluation)
            "reason": agent_result["reason"],                            # Agent's reasoning
            "mcp_tool_used": agent_result.get("mcp_tool_used", False),  # MCP tool usage flag
            "mcp_tool_name": agent_result.get("mcp_tool_name"),         # MCP tool name if used
            "mcp_tool_details": agent_result.get("mcp_tool_details"),   # MCP tool details if used
            "chunk_hierarchy": agent_result.get("chunk_hierarchy", []), # Parent-child chunk relationships (needle)
            "map_reduce_steps": agent_result.get("map_reduce_steps"),   # Map-reduce process visualization (summary)
        }
        
        # Display result
        print(f"✓ Route:      {unified_response['route'].upper()}")
        print(f"✓ Answer:     {unified_response['answer']}")
        print(f"✓ Confidence: {unified_response['confidence']:.2f}")
        print(f"✓ Sources:    {len(unified_response['sources'])} chunk(s)")
        print(f"✓ Reason:     {unified_response['reason']}")
        if unified_response["mcp_tool_used"]:
            print(f"✓ MCP Tool:   🔧 {unified_response['mcp_tool_name']}")
        
        print("\n" + "="*70)
        print("✅ RAG PIPELINE COMPLETED")
        print("="*70)
        
        return unified_response


# ====================================================
# FACTORY FUNCTION - Clean interface
# ====================================================

def create_orchestrator(
    router_agent,
    needle_agent,
    summary_agent,
    needle_retriever,
    summary_retriever,
) -> Orchestrator:
    """
    Factory function to create an Orchestrator.
    
    WHY: Provides clean interface for creating orchestrator.
    
    Args:
        router_agent: RouterAgent instance
        needle_agent: NeedleAgent instance
        summary_agent: SummaryAgent instance
        needle_retriever: Needle retriever from Index Layer
        summary_retriever: Summary retriever from Index Layer
    
    Returns:
        Configured Orchestrator instance
    """
    return Orchestrator(
        router_agent=router_agent,
        needle_agent=needle_agent,
        summary_agent=summary_agent,
        needle_retriever=needle_retriever,
        summary_retriever=summary_retriever,
    )

