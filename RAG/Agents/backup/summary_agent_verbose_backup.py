"""
====================================================
SUMMARY AGENT - CONTEXTUAL SYNTHESIS
====================================================

RESPONSIBILITY:
This agent answers CONTEXTUAL questions requiring broad understanding.
It does NOT extract single facts (use Needle Agent).
It does NOT guess missing information.
It ONLY synthesizes retrieved context into coherent explanations.

WHY THIS EXISTS:
- Some questions need multiple facts and narrative flow
- Summary questions require high recall, not just precision
- Different retrieval strategy: merged hierarchical chunks
- Context matters more than atomic precision

WHY LANGCHAIN:
- LangChain excels at LLM orchestration and synthesis
- Clear separation: retrieval (LlamaIndex) vs synthesis (LangChain)
- Retriever is injected as dependency

WHY NO RETRIEVAL HERE:
- Retriever is built by Index Layer
- Retriever encapsulates Auto-Merging logic
- Agent only synthesizes what retriever returns
- Separation of concerns

CRITICAL RULES:
- NEVER build retrievers
- NEVER access FAISS
- NEVER create embeddings
- NEVER guess missing information
- ONLY synthesize retrieved context
- If context insufficient, acknowledge it

====================================================
"""

import os
import json
from typing import Dict, Any, List
from pydantic import BaseModel, Field

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

# MCP Tool: Date Difference Calculator
# WHY: LLMs are poor at deterministic date arithmetic
# - Forget leap years, month boundaries
# - Approximate instead of calculating exactly
# - This tool provides guaranteed accuracy
try:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from mcp_tools.date_calculator import calculate_days_between
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False


# ====================================================
# OUTPUT SCHEMA - Enforces structured response
# ====================================================

class SummaryAnswer(BaseModel):
    """
    Structured output for summary question answering.
    
    WHY PYDANTIC:
    - Enforces exact schema
    - Automatic validation
    - Type safety
    - Handles edge cases cleanly
    
    WHY THESE FIELDS:
    - answer: The synthesized explanation (always present)
    - confidence: How well the context covers the question
    - sources: Which chunk IDs were used (traceability)
    - reason: Human-readable explanation (debugging)
    """
    answer: str = Field(
        description="The synthesized answer from retrieved context. "
                    "If context is insufficient, explain what is missing."
    )
    confidence: float = Field(
        description="Confidence score between 0.0 and 1.0. "
                    "High (>0.7) if context fully covers question. "
                    "Low (≤0.3) if context is insufficient.",
        ge=0.0,
        le=1.0
    )
    sources: List[str] = Field(
        description="List of chunk IDs (parent and/or child) that were used",
        default_factory=list
    )
    reason: str = Field(
        description="Brief explanation of confidence and coverage"
    )


# ====================================================
# SUMMARY AGENT - Contextual Synthesis
# ====================================================

class SummaryAgent:
    """
    Production-grade contextual synthesizer for RAG system.
    
    Answers questions that require broad understanding:
    - Explanations, overviews, narratives
    - Multiple facts combined coherently
    - High recall > high precision
    
    WHY THIS AGENT:
    - Different from Needle (many facts vs one fact)
    - Uses merged hierarchical chunks (parent+child)
    - Synthesizes context into coherent explanation
    - No similarity threshold (high recall)
    
    WHY SEPARATE FROM NEEDLE AGENT:
    - Different retrieval strategy (Auto-Merging)
    - Different LLM temperature (0.2 vs 0.0)
    - Different prompt (synthesis vs extraction)
    - Different use cases (context vs precision)
    
    ARCHITECTURE:
    - Uses ChatOpenAI for synthesis
    - Structured output (Pydantic)
    - Low temperature (0.2 = coherent but factual)
    - Strict prompt (forbids guessing)
    """
    
    def __init__(
        self,
        model: str = "gpt-4o-mini",
        temperature: float = 0.2,
        enable_mcp_tools: bool = True,
    ):
        """
        Initialize the Summary Agent.
        
        Args:
            model: OpenAI model for synthesis
                   (gpt-4o-mini is fast and cheap, good for synthesis)
            temperature: LLM temperature (0.2 = coherent without creativity)
            enable_mcp_tools: Enable MCP tools for deterministic computation
                             (default: True if available)
        
        WHY THESE DEFAULTS:
        - gpt-4o-mini: Fast, cheap, good at synthesis
        - temperature=0.2: Balance between consistency and coherence
                          Higher than Needle (0.0) for better flow
                          Lower than creative tasks (0.7+)
        - enable_mcp_tools: Delegates date arithmetic to external tools
        """
        # Validate OpenAI API key
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError(
                "OPENAI_API_KEY not found. "
                "Set it in environment or .env file."
            )
        
        self.model = model
        self.temperature = temperature
        self.enable_mcp_tools = enable_mcp_tools and MCP_AVAILABLE
        
        # Initialize LLM
        # WHY: ChatOpenAI provides consistent, structured outputs
        self.llm = ChatOpenAI(
            model=self.model,
            temperature=self.temperature,
        )
        
        # Define MCP tools if enabled
        # WHY: Provides deterministic date calculations
        # WHY NOT IN PROMPT: LLMs cannot reliably do date arithmetic
        self.tools = self._define_mcp_tools() if self.enable_mcp_tools else []
        
        # Initialize output parser
        # WHY: Enforces structured response, handles edge cases
        self.parser = PydanticOutputParser(pydantic_object=SummaryAnswer)
        
        # Build prompt
        # WHY: Prompt design is critical for grounded synthesis
        self.prompt = self._build_prompt()
        
        print(f"✅ Summary Agent initialized")
        print(f"   Model: {self.model}")
        print(f"   Temperature: {self.temperature}")
        print(f"   Output: Structured (Pydantic)")
        print(f"   Policy: CONTEXT-GROUNDED SYNTHESIS")
        print(f"   MCP Tools: {'✅ Enabled' if self.enable_mcp_tools else '❌ Disabled'}")
    
    def _define_mcp_tools(self) -> List[Dict[str, Any]]:
        """
        Define MCP tools available to this agent.
        
        WHY MCP TOOLS:
        - LLMs are fundamentally poor at arithmetic
        - Date calculations require precision (leap years, month boundaries)
        - Prompting alone cannot guarantee correctness
        - External tools provide deterministic, verifiable results
        
        Returns:
            List of tool definitions in OpenAI function calling format
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "calculate_days_between",
                    "description": """Calculate the exact number of days between two dates.
                    
                    WHEN TO USE:
                    - Question asks about days between dates
                    - Question asks "how long" or "time difference"
                    - Synthesizing timeline with precise durations
                    
                    CRITICAL:
                    - Dates are in the retrieved CONTEXT
                    - Extract dates in YYYY-MM-DD format
                    - NEVER estimate or approximate date differences
                    - ALWAYS use this tool for date calculations""",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "start_date": {
                                "type": "string",
                                "description": "Start date in YYYY-MM-DD format (extract from context)"
                            },
                            "end_date": {
                                "type": "string",
                                "description": "End date in YYYY-MM-DD format (extract from context)"
                            }
                        },
                        "required": ["start_date", "end_date"]
                    }
                }
            }
        ]
    
    def _build_prompt(self) -> ChatPromptTemplate:
        """
        Build the summary synthesis prompt.
        
        WHY THIS PROMPT STRUCTURE:
        - Explicit role definition (synthesizer, not guesser)
        - Clear instruction to use ALL relevant context
        - MCP tool instructions for date calculations
        - Examples for few-shot learning
        - Format instructions for structured output
        - Explicit constraints (evidence required)
        
        Returns:
            ChatPromptTemplate for context synthesis
        """
        
        # Add MCP tool instructions if enabled
        mcp_instructions = ""
        if self.enable_mcp_tools:
            mcp_instructions = """
5. ⚠️  USE MCP TOOLS for date calculations

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MCP TOOL: DATE DIFFERENCE CALCULATOR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

If a question requires precise or deterministic date computation
(e.g. number of days between dates), you MUST use the Date Difference
tool instead of calculating the result yourself.

WHY NOT CALCULATE YOURSELF:
- LLMs cannot reliably do date arithmetic
- Forget leap years, month boundaries, edge cases
- Approximations ("about 25 days") are unacceptable
- External tool guarantees exact, verifiable results

WHEN TO USE THE TOOL:
✅ "How many days between X and Y?"
✅ Synthesizing timeline with precise durations
✅ "How long from accident to repair?"

WHEN NOT TO USE:
❌ General summaries without date arithmetic
❌ Explanations not involving duration
❌ Questions not requiring calculations

HOW TO USE:
1. Extract dates from CONTEXT in YYYY-MM-DD format
2. Call calculate_days_between(start_date, end_date)
3. Integrate the exact result into your narrative
4. Never approximate or estimate

Example:
Context: "Accident: 2024-01-24, Repair: 2024-02-18"
Query: "Describe the timeline"
Action: Call calculate_days_between('2024-01-24', '2024-02-18')
Result: 25 days
Answer: "The accident occurred on January 24, 2024. The repair was 
scheduled for February 18, exactly 25 days later."

"""
        
        template = """You are an EXPERT CONTEXT SYNTHESIZER for a RAG system.

Your mission: Provide comprehensive, well-structured answers using ALL available context.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚨 ABSOLUTE RULES (NEVER VIOLATE)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. ⛔ NEVER add external knowledge or assumptions
2. ⛔ NEVER fabricate facts not in retrieved chunks
3. ⛔ NEVER ignore relevant information from chunks
4. ⛔ NEVER give single-fact answers (that's Needle Agent's job)
5. ✅ ALWAYS synthesize multiple pieces of information
6. ✅ ALWAYS use comprehensive context from ALL chunks
7. ✅ ALWAYS acknowledge when information is incomplete

If context is insufficient:
→ Synthesize what IS available
→ Explicitly state what is MISSING
→ Lower confidence score (≤ 0.4)
→ Explain coverage gaps in reason field

TRANSPARENCY > COMPLETENESS. Tell users what you DON'T know.
""" + mcp_instructions + """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 SYNTHESIS STRATEGIES (Match to Question Type)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔹 For EXPLANATORY questions ("Describe...", "Explain...", "What happened..."):
   → Narrative synthesis: Combine facts into coherent story
   → Include: who, what, when, where, why (when available)
   → Structure: chronological or logical flow
   → Length: 2-4 sentences minimum

🔹 For AGGREGATE questions ("How many...", "List all...", "Total..."):
   → Comprehensive enumeration: Count/list ALL instances
   → Scan EVERY chunk for relevant entities
   → Format: Clear list or explicit count
   → Verify: Did you check all {num_chunks} chunks?
   → Length: Complete list, don't truncate

🔹 For COMPARISON questions ("Compare...", "Difference between..."):
   → Side-by-side analysis: Extract facts for each entity
   → Structure: Point-by-point or entity-by-entity
   → Highlight: Similarities AND differences
   → Length: Fair coverage of both sides

🔹 For CONTEXTUAL questions ("Tell me about...", "Overview of..."):
   → Holistic synthesis: Provide full picture
   → Include: All relevant aspects from chunks
   → Organize: By theme or importance
   → Length: Comprehensive paragraph(s)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ ANSWER QUALITY STANDARDS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Excellent Answer:
✓ Synthesizes information from multiple chunks
✓ Well-organized and easy to follow
✓ Comprehensive (uses ALL relevant context)
✓ Factually accurate (nothing made up)
✓ Appropriate length (2-5 sentences for narratives)
✓ Acknowledges limitations if context incomplete

Poor Answer:
✗ Single isolated fact (should be Needle)
✗ Adds information not in chunks
✗ Ignores relevant chunks
✗ Disorganized or hard to follow
✗ Too brief for the question scope
✗ Claims completeness when context is partial

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📚 EXAMPLES (Learn from these)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Example 1 - Narrative Synthesis:
Question: "Describe the accident circumstances."
Chunks (3 retrieved):
  - "Accident occurred on January 10, 2024 at 3:00 PM"
  - "Location: Interstate 95, northbound lane, near Exit 23"
  - "Weather: Heavy rain, poor visibility. Road conditions: wet pavement"
  - "Vehicles: 2020 Honda Accord (rear vehicle) rear-ended 2019 Toyota Camry (lead vehicle)"
✓ Answer: "The accident occurred on January 10, 2024 at 3:00 PM on Interstate 95's 
northbound lane near Exit 23. Weather conditions were challenging, with heavy rain 
causing poor visibility and wet pavement. The incident involved a 2020 Honda Accord 
that rear-ended a 2019 Toyota Camry."
✓ Confidence: 0.90
✓ Reason: "Comprehensive synthesis of accident details from multiple chunks"

✅ Example 2 - Aggregate/Count (CRITICAL):
Question: "How many claims are in the document?"
Chunks (30 retrieved - MUST scan ALL):
  - Chunks mention: Claim #1, Claim #2, Claim #3... Claim #20
✓ Answer: "There are 20 claims in the document, numbered from Claim #1 through Claim #20."
✓ Confidence: 0.95
✓ Reason: "Systematically counted all claim numbers across all 30 retrieved chunks"
⚠️  Note: Count MUST be accurate! Scan every chunk!

✅ Example 3 - Comprehensive List:
Question: "What vehicles are mentioned in the document?"
Chunks (25 retrieved):
  - Various chunks mention different vehicles
✓ Answer: "The document mentions the following vehicles: 2020 Honda Accord (Claim #1), 
2019 Toyota Camry (Claim #1), 2021 Ford F-150 (Claim #3), 2018 Tesla Model 3 (Claim #5), 
2022 BMW X5 (Claim #7). This list covers all vehicles explicitly identified across 
the retrieved context."
✓ Confidence: 0.85
✓ Reason: "Comprehensive enumeration from all chunks, organized by claim"

✅ Example 4 - Comparison:
Question: "Compare claims #1 and #5."
Chunks: [Details about both claims]
✓ Answer: "Claim #1 involves a rear-end collision on I-95 with $4,500 in damages to a 
Honda Accord, filed by Jon Mor on Jan 10. Claim #5 involves a side-impact collision 
in a parking lot with $2,300 in damages to a Tesla Model 3, filed by Sarah Klein on 
Feb 2. Key differences: accident type (rear-end vs. side-impact), location (highway 
vs. parking lot), and damage severity."
✓ Confidence: 0.85
✓ Reason: "Side-by-side comparison synthesizing details from both claims"

❌ Example 5 - Partial Context (HONEST):
Question: "Explain the claims processing timeline."
Chunks:
  - "Claim filed: Jan 10, 2024"
  - "Adjuster assigned: Jan 12, 2024"
  - [No other timeline info]
✓ Answer: "Based on the available context, the claim was filed on January 10, 2024, 
and an adjuster was assigned two days later on January 12, 2024. However, the 
retrieved information does not include details about subsequent processing steps, 
resolution timeline, or final disposition."
✓ Confidence: 0.35
✓ Reason: "Partial coverage - only initial steps available. Missing: processing stages, resolution."
⚠️  Note: HONEST about gaps! Don't invent timeline!

❌ Example 6 - Wrong Approach (DON'T DO THIS):
Question: "How many claims involve Honda vehicles?"
❌ Bad Answer: "There are 3 claims." [Just counted visible chunks, didn't scan all]
✓ Good Answer: "Based on scanning all 30 retrieved chunks, there are 5 claims 
involving Honda vehicles: Claims #1, #4, #8, #12, and #17. This represents 25% 
of the total 20 claims in the document."
⚠️  Note: MUST scan ALL chunks for aggregates!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RETRIEVED CONTEXT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{chunks}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
QUESTION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{question}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT FORMAT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{format_instructions}

Synthesize the context above into a coherent answer. Use all relevant information.
"""
        
        return ChatPromptTemplate.from_template(template)
    
    def answer(self, question: str, retriever=None, query_engine=None) -> Dict[str, Any]:
        """
        Answer a summary question using MapReduce or simple retrieval.
        
        This is the main public method of the Summary Agent.
        
        Args:
            question: User's summary question (e.g., "Describe the incident")
            retriever: Pre-built Summary Retriever from Index Layer (legacy mode)
                      Must have .retrieve(question) method
                      Uses simple concatenation
            query_engine: MapReduce Query Engine from Index Layer (recommended)
                         Must have .query(question) method
                         Uses tree_summarize (MapReduce)
        
        Returns:
            Dictionary with:
                - answer: str (synthesized explanation)
                - confidence: float (0.0 to 1.0)
                - sources: list of chunk IDs used
                - reason: str (explanation of coverage)
        
        WHY TWO MODES:
        - query_engine (MapReduce): Better for comprehensive summaries
        - retriever (Simple): Faster, good for specific questions
        - Prefer query_engine if provided
        
        HOW MAP-REDUCE WORKS:
        1. Query engine retrieves relevant chunks (top-k=15)
        2. MAP: Each chunk is summarized individually
        3. REDUCE: Summaries are recursively combined
        4. FINAL: Comprehensive summary is produced
        
        WHY THIS IS BETTER:
        - Can handle 50+ chunks efficiently
        - Hierarchical combination prevents context overload
        - Better quality for complex multi-part summaries
        - Systematic processing of all relevant information
        """
        if not question or not question.strip():
            raise ValueError("Question cannot be empty")
        
        if retriever is None and query_engine is None:
            raise ValueError("Must provide either retriever or query_engine")
        
        # PREFERRED: Use MapReduce query engine if provided
        if query_engine is not None:
            return self._answer_with_map_reduce(question, query_engine)
        
        # FALLBACK: Use simple retrieval + synthesis
        return self._answer_with_retriever(question, retriever)
    
    def _answer_with_map_reduce(self, question: str, query_engine) -> Dict[str, Any]:
        """
        Answer using MapReduce (tree_summarize).
        
        WHY SEPARATE METHOD:
        - Clean separation of MapReduce vs simple retrieval
        - MapReduce is handled entirely by query_engine
        - Agent just wraps the response in standard format
        
        Args:
            question: User's question
            query_engine: RetrieverQueryEngine with tree_summarize
        
        Returns:
            Dictionary with answer, confidence, sources, reason
        """
        print(f"\n🗺️  Using MAP-REDUCE for comprehensive summarization...")
        print(f"   Question: '{question}'")
        
        # Query the MapReduce engine
        # WHY: Query engine handles retrieval + map + reduce automatically
        response = query_engine.query(question.strip())
        
        # Extract answer from response
        answer_text = str(response)
        
        # Get source nodes if available
        source_nodes = getattr(response, 'source_nodes', [])
        chunk_ids = [node.node_id for node in source_nodes]
        chunk_contents = [node.text for node in source_nodes]  # Extract actual text
        
        print(f"   ✅ Generated summary using {len(chunk_ids)} chunk(s)")
        
        # Return standardized format
        # WHY: Consistent interface for orchestrator
        # WHY: Include chunk_contents for evaluation (Context Relevancy metric)
        return {
            "answer": answer_text,
            "confidence": 0.85,  # High confidence for MapReduce
            "sources": chunk_ids,
            "retrieved_chunks_content": chunk_contents,  # For evaluation
            "reason": f"MapReduce hierarchical summarization of {len(chunk_ids)} chunks"
        }
    
    def _answer_with_retriever(self, question: str, retriever) -> Dict[str, Any]:
        """
        Answer using simple retrieval + synthesis (legacy mode).
        
        WHY THIS METHOD:
        - Backward compatibility
        - Faster for simple questions
        - Uses LangChain structured output
        
        Args:
            question: User's question
            retriever: VectorIndexRetriever
        
        Returns:
            Dictionary with answer, confidence, sources, reason
        """
        
        # Step 1: Retrieve merged hierarchical chunks
        # WHY: Retriever returns parent chunks when children match
        # WHY: Auto-Merging provides broader context automatically
        # WHY: No similarity threshold for high recall
        print(f"\n📚 Retrieving context for: '{question}'")
        retrieved_nodes = retriever.retrieve(question.strip())
        
        # Step 2: Check if any chunks were retrieved
        # WHY: If retriever returns nothing, we acknowledge insufficient context
        # WHY: Unlike Needle Agent, we still provide an answer explaining the gap
        if not retrieved_nodes or len(retrieved_nodes) == 0:
            print("   ⚠️  No context retrieved")
            return {
                "answer": "No relevant context was found to answer this question. "
                         "The available information does not cover the requested topic.",
                "confidence": 0.1,
                "sources": [],
                "retrieved_chunks_content": [],  # No chunks retrieved
                "reason": "No context retrieved from the knowledge base"
            }
        
        print(f"   ✅ Retrieved {len(retrieved_nodes)} chunk(s)")
        
        # Step 3: Format chunks for LLM
        # WHY: LLM needs text content and chunk IDs for traceability
        # WHY: Each chunk may be parent or child (Auto-Merging decides)
        chunks_text = ""
        chunk_ids = []
        chunk_contents = []  # Store actual content for evaluation
        
        for i, node in enumerate(retrieved_nodes, 1):
            chunk_id = node.node.node_id  # LlamaIndex node ID
            chunk_text = node.node.text    # Actual text content (may be merged)
            chunk_score = node.score       # Similarity score (informational)
            
            chunks_text += f"\n[Chunk {i}] ID: {chunk_id}\n"
            chunks_text += f"Relevance: {chunk_score:.3f}\n"
            chunks_text += f"Content:\n{chunk_text}\n"
            chunks_text += "─" * 60 + "\n"
            
            chunk_ids.append(chunk_id)
            chunk_contents.append(chunk_text)  # Save for evaluation
        
        # Step 4: Format prompt with question and chunks
        # WHY: Combines template with specific question and retrieved context
        formatted_prompt = self.prompt.format_messages(
            question=question.strip(),
            chunks=chunks_text,
            format_instructions=self.parser.get_format_instructions()
        )
        
        # Convert to message format for tool calling
        messages = [{"role": msg.type, "content": msg.content} for msg in formatted_prompt]
        
        # Step 5: Get LLM response (with optional MCP tools)
        # WHY: LLM synthesizes context into coherent explanation
        # WHY: Temperature=0.2 ensures coherence without hallucination
        # WHY: Tools enabled: LLM can delegate date calculations to MCP
        print(f"   🤖 Synthesizing answer with {self.model}...")
        
        if self.enable_mcp_tools:
            print(f"   🔧 MCP tools enabled - LLM can use tools if needed")
            response = self.llm.invoke(
                messages,
                tools=self.tools,
                tool_choice="auto"  # LLM decides when to use tools
            )
            
            # Handle tool calls if LLM decided to use them
            if hasattr(response, 'tool_calls') and response.tool_calls:
                return self._handle_tool_call(response, messages, chunk_contents)
        else:
            response = self.llm.invoke(messages)
        
        # Step 6: Parse structured output (no tools used)
        # WHY: Validates response matches SummaryAnswer schema
        # WHY: Handles edge cases gracefully
        content = response.content if isinstance(response.content, str) else str(response.content)
        result: SummaryAnswer = self.parser.parse(content)
        
        # Step 7: Convert to dictionary and return
        # WHY: Standard Python dict for easy JSON serialization
        # WHY: Include chunk_contents for evaluation (Context Relevancy metric)
        return {
            "answer": result.answer,
            "confidence": result.confidence,
            "sources": result.sources,
            "retrieved_chunks_content": chunk_contents,  # For evaluation
            "reason": result.reason
        }
    
    def _handle_tool_call(
        self,
        response,
        messages: List[Dict],
        chunk_contents: List[str]
    ) -> Dict[str, Any]:
        """
        Handle MCP tool call from LLM.
        
        WHY THIS METHOD:
        - LLM decided a tool is needed (date calculation)
        - Execute the tool with provided arguments
        - Send result back to LLM for final formatting
        
        Args:
            response: LLM response containing tool call
            messages: Conversation history
            chunk_contents: Retrieved chunk texts
        
        Returns:
            Final answer dictionary
        """
        print(f"   🔧 LLM called MCP tool for date calculation")
        
        for tool_call in response.tool_calls:
            tool_name = tool_call['name']
            tool_args = tool_call['args']
            tool_id = tool_call['id']
            
            if tool_name == 'calculate_days_between':
                # Execute the MCP tool
                # WHY: Provides exact, deterministic date arithmetic
                start = tool_args['start_date']
                end = tool_args['end_date']
                
                print(f"      Calculating: {start} to {end}")
                tool_result = calculate_days_between(start, end)
                
                print(f"      Result: {tool_result['number_of_days']} days")
                
                # Send tool result back to LLM
                messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "name": tool_name,
                        "args": tool_args,
                        "id": tool_id,
                        "type": "tool_call"
                    }]
                })
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_id,
                    "name": tool_name,
                    "content": json.dumps(tool_result)
                })
                
                # Get final answer from LLM
                print(f"   🤖 LLM formatting answer with tool result...")
                final_response = self.llm.invoke(messages)
                
                # Parse the final answer
                content = final_response.content if isinstance(final_response.content, str) else str(final_response.content)
                result: SummaryAnswer = self.parser.parse(content)
                
                return {
                    "answer": result.answer,
                    "confidence": result.confidence,
                    "sources": result.sources,
                    "retrieved_chunks_content": chunk_contents,
                    "reason": result.reason + " (Used MCP: calculate_days_between)"
                }
        
        # Fallback if tool call failed
        return {
            "answer": "Tool call failed - unable to calculate date difference",
            "confidence": 0.0,
            "sources": [],
            "retrieved_chunks_content": chunk_contents,
            "reason": "Tool call failed"
        }


# ====================================================
# FACTORY FUNCTION - Clean interface
# ====================================================

def create_summary_agent(
    model: str = "gpt-4o-mini",
    temperature: float = 0.2,
    enable_mcp_tools: bool = True,
) -> SummaryAgent:
    """
    Factory function to create a Summary Agent.
    
    WHY: Provides clean interface for importing and using this agent.
    
    Args:
        model: OpenAI model name
        temperature: LLM temperature (0.2 = coherent synthesis)
        enable_mcp_tools: Enable MCP tools for date calculations (default: True)
    
    Returns:
        Configured SummaryAgent instance
    """
    return SummaryAgent(
        model=model,
        temperature=temperature,
        enable_mcp_tools=enable_mcp_tools,
    )

