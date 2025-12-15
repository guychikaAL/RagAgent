"""
====================================================
NEEDLE AGENT - ATOMIC FACT EXTRACTION
====================================================

RESPONSIBILITY:
This agent answers HIGH-PRECISION questions using atomic facts.
It does NOT summarize.
It does NOT guess.
It does NOT hallucinate.
It ONLY returns facts explicitly found in retrieved chunks.

WHY THIS EXISTS:
- Some questions need ONE exact fact (phone number, date, name)
- Needle questions require high precision, not high recall
- Wrong answer is worse than no answer
- Atomic chunks contain isolated, verifiable facts

WHY LANGCHAIN:
- LangChain excels at LLM orchestration and structured outputs
- Clear separation: retrieval (LlamaIndex) vs answering (LangChain)
- Retriever is injected, agent only extracts facts

WHY NO RETRIEVAL HERE:
- Retriever is built by Index Layer
- Retriever is injected as dependency
- Agent only processes what retriever returns
- Separation of concerns

CRITICAL RULES:
- NEVER build retrievers
- NEVER access FAISS
- NEVER create embeddings
- NEVER guess or infer
- ONLY return what is explicitly stated
- If not found, return null

====================================================
"""

import os
import json
from typing import Dict, Any, Optional, List
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

class NeedleAnswer(BaseModel):
    """
    Structured output for needle question answering.
    
    WHY PYDANTIC:
    - Enforces exact schema
    - Automatic validation
    - Type safety
    - Handles null answers cleanly
    
    WHY THESE FIELDS:
    - answer: The extracted fact (null if not found)
    - confidence: How certain we are (0.0 if not found)
    - sources: Which chunk IDs were used (traceability)
    - reason: Human-readable explanation (debugging)
    """
    answer: Optional[str] = Field(
        description="The exact answer extracted from chunks, or null if not found",
        default=None
    )
    confidence: float = Field(
        description="Confidence score between 0.0 and 1.0",
        ge=0.0,
        le=1.0
    )
    sources: List[str] = Field(
        description="List of chunk IDs that were used",
        default_factory=list
    )
    reason: str = Field(
        description="Brief explanation of why this answer was given (or not given)"
    )


# ====================================================
# NEEDLE AGENT - Atomic Fact Extraction
# ====================================================

class NeedleAgent:
    """
    Production-grade atomic fact extractor for RAG system.
    
    Answers questions that require ONE atomic fact:
    - Names, numbers, dates, times, identifiers
    - Questions with single, verifiable answers
    - High precision > high recall
    
    WHY THIS AGENT:
    - Different from summary (one fact vs many facts)
    - Never guesses (null answer if uncertain)
    - Grounded in retrieved text (no hallucination)
    - Traceable (returns source chunk IDs)
    
    WHY SEPARATE FROM RETRIEVAL:
    - Retrieval is vector search (LlamaIndex)
    - Answering is fact extraction (LangChain LLM)
    - Retriever is injected (dependency injection pattern)
    - Can swap retrieval without changing answering logic
    
    ARCHITECTURE:
    - Uses ChatOpenAI for fact extraction
    - Structured output (Pydantic)
    - Zero temperature (deterministic)
    - Strict prompt (forbids guessing)
    """
    
    def __init__(
        self,
        model: str = "gpt-4o-mini",
        temperature: float = 0.0,
        enable_mcp_tools: bool = True,
    ):
        """
        Initialize the Needle Agent.
        
        Args:
            model: OpenAI model for fact extraction
                   (gpt-4o-mini is fast and cheap, sufficient for extraction)
            temperature: LLM temperature (0.0 = deterministic, no creativity)
            enable_mcp_tools: Enable MCP tools for deterministic computation
                             (default: True if available)
        
        WHY THESE DEFAULTS:
        - gpt-4o-mini: Fast, cheap, good at fact extraction
        - temperature=0.0: Facts must be deterministic and consistent
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
        # WHY: Enforces structured response, handles null answers properly
        self.parser = PydanticOutputParser(pydantic_object=NeedleAnswer)
        
        # Build prompt
        # WHY: Prompt design is critical for preventing hallucination
        self.prompt = self._build_prompt()
        
        print(f"✅ Needle Agent initialized")
        print(f"   Model: {self.model}")
        print(f"   Temperature: {self.temperature}")
        print(f"   Output: Structured (Pydantic)")
        print(f"   Policy: NO GUESSING")
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
                    - Requires precise date arithmetic
                    
                    CRITICAL:
                    - Dates are in the retrieved CONTEXT, not the query
                    - Extract dates from chunks in YYYY-MM-DD format
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
        Build the needle answering prompt.
        
        WHY THIS PROMPT STRUCTURE:
        - Explicit role definition (fact extractor, not summarizer)
        - Clear instruction to never guess
        - MCP tool instructions for date calculations
        - Examples for few-shot learning
        - Format instructions for structured output
        - Explicit constraints (evidence required)
        
        Returns:
            ChatPromptTemplate for fact extraction
        """
        
        # Add MCP tool instructions if enabled
        mcp_instructions = ""
        if self.enable_mcp_tools:
            mcp_instructions = """
5. ⚠️  USE MCP TOOLS for date calculations

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MCP TOOL: DATE DIFFERENCE CALCULATOR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

If a question asks about the NUMBER OF DAYS or TIME DIFFERENCE between 
two dates, you MUST:
1. Find BOTH dates in the retrieved chunks
2. Convert dates to YYYY-MM-DD format (e.g., "2024-02-14")
3. Call the calculate_days_between tool
4. Use the EXACT result in your answer

⚠️  CRITICAL: You MUST use this tool for ANY date arithmetic question!

WHY NOT CALCULATE YOURSELF:
- LLMs cannot reliably do date arithmetic
- Forget leap years, month boundaries, edge cases
- Approximations ("about 25 days") are unacceptable
- External tool guarantees exact, verifiable results

WHEN TO USE THE TOOL (MANDATORY):
✅ "How many days between X and Y?"
✅ "How many days from [date field] to [date field]?"
✅ "What is the time gap between these dates?"
✅ "How long from accident to repair?"
✅ "Days between Date of Incident and Repair Appointment Date?"

WHEN NOT TO USE:
❌ Simple fact extraction (phone numbers, names, single dates)
❌ Summaries or explanations
❌ Questions asking for a single date (not a difference)

HOW TO USE (STEP BY STEP):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Step 1: IDENTIFY that this is a date arithmetic question
   → Look for keywords: "how many days", "difference", "between", "from...to"

Step 2: FIND BOTH DATES in the retrieved chunks
   → Look for field names like:
     • "Date of Incident"
     • "Repair Appointment Date"  
     • Date fields in context
   → Example: "Date of Incident: 2024-02-14"
   → Example: "Repair Appointment Date: 2024-03-05"

Step 3: CONVERT dates to YYYY-MM-DD format
   → If already in YYYY-MM-DD format, use as-is
   → If in another format, convert:
     • "January 24, 2024" → "2024-01-24"
     • "02/14/2024" → "2024-02-14"

Step 4: CALL THE TOOL with both dates
   → Function: calculate_days_between(start_date, end_date)
   → start_date: The earlier date (e.g., Date of Incident)
   → end_date: The later date (e.g., Repair Appointment Date)

Step 5: USE THE EXACT RESULT
   → The tool returns: {"number_of_days": 20}
   → Your answer: "20 days"
   → NEVER estimate or approximate!

EXAMPLE WORKFLOW:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Query: "How many days between David Ross's Date of Incident and Repair Appointment Date?"

Retrieved Context:
"Name: David Ross
Date of Incident: 2024-02-14
Repair Appointment Date: 2024-03-05"

Step 1: ✓ This is a date arithmetic question (keyword: "how many days between")
Step 2: ✓ Found both dates:
        - Date of Incident: 2024-02-14
        - Repair Appointment Date: 2024-03-05
Step 3: ✓ Dates already in YYYY-MM-DD format
Step 4: ✓ Call tool: calculate_days_between('2024-02-14', '2024-03-05')
Step 5: ✓ Tool returns: {"number_of_days": 20}
        ✓ Final Answer: "20 days"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  REMEMBER: If the question asks about days between dates, 
              YOU MUST use this tool. NO EXCEPTIONS!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
        
        template = """You are a PRECISION FACT EXTRACTOR for a RAG system.

Your mission: Extract ONE atomic fact with ZERO hallucination.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚨 ABSOLUTE RULES (NEVER VIOLATE)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. ⛔ NEVER guess, infer, or extrapolate
2. ⛔ NEVER use external knowledge or assumptions
3. ⛔ NEVER combine multiple facts into one answer
4. ⛔ NEVER approximate when precision is required
5. ✅ ONLY extract what is EXPLICITLY and DIRECTLY stated

If the EXACT answer is not in the chunks:
→ answer: null
→ confidence: 0.0
→ reason: "Fact not found in retrieved context"

BETTER TO SAY "I DON'T KNOW" THAN TO GUESS WRONG.
""" + mcp_instructions + """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 EXTRACTION PROCESS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Step 1: Parse question
   → Identify: What specific fact is being asked?
   → Identify: About which entity? (person, claim, vehicle, etc.)

Step 2: Scan chunks systematically
   → For each chunk, check: Does it contain the EXACT fact?
   → Match: Entity name + requested attribute
   → Verify: Is the information direct and unambiguous?

Step 3: Extract with precision
   → Copy the exact value (number, name, date, identifier)
   → Keep format consistent (preserve units, formatting)
   → Use minimal words (shortest correct answer)

Step 4: Validate extraction
   → Can you point to exact text in chunk? (Yes = extract, No = null)
   → Is this the DIRECT answer or an inference? (Direct only!)
   → Is this about the RIGHT entity mentioned in question?

Step 5: Assign confidence
   → 0.95: Perfect match, unambiguous
   → 0.85: Clear match, minor ambiguity
   → 0.70: Correct but requires interpretation
   → 0.00: Not found or requires guessing

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ ANSWER QUALITY CHECKLIST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Good Answer:
✓ 1-10 words maximum (atomic fact)
✓ Directly copied or minimally paraphrased from chunk
✓ Answers the EXACT question asked
✓ Verifiable by reading the source chunk
✓ About the correct entity/claim
✓ Preserves original units/format

Bad Answer:
✗ Combines multiple facts
✗ Adds interpretation or context
✗ Uses information not in chunks
✗ About different entity than asked
✗ Approximates instead of exact value
✗ Hedges ("probably", "might be", "around")

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📚 EXAMPLES (Learn from these)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Example 1 - Perfect Match:
Question: "What is Jon Mor's phone number?"
Chunk: "Claimant: Jon Mor, Phone: (555) 100-2000, Email: jmor@example.com"
✓ Answer: "(555) 100-2000"
✓ Confidence: 0.95
✓ Reason: "Exact match found in claimant contact information"

✅ Example 2 - Entity-Specific:
Question: "What is the VIN for claim #3?"
Chunk 1: "Claim #2, Vehicle VIN: 1HGBH41JXMN109186"
Chunk 2: "Claim #3, Vehicle VIN: 5NPEB4AC2DH123456"
✓ Answer: "5NPEB4AC2DH123456"
✓ Confidence: 0.95
✓ Reason: "VIN found for correct claim number"
Note: Ignored Chunk 1 (wrong claim)

✅ Example 3 - Unit Preservation:
Question: "What was the repair cost?"
Chunk: "Total repair estimate: $3,847.50"
✓ Answer: "$3,847.50"
✓ Confidence: 0.95
✓ Reason: "Exact amount with currency symbol preserved"

❌ Example 4 - Not Found:
Question: "What is the claimant's Social Security Number?"
Chunk: "Claimant: Jon Mor, Phone: (555) 100-2000"
✓ Answer: null
✓ Confidence: 0.0
✓ Reason: "SSN not present in retrieved context"
Note: NO GUESSING, even if other info is present!

❌ Example 5 - Wrong Entity:
Question: "What is Sarah Klein's phone number?"
Chunk: "Claim filed by John Doe, Phone: (555) 222-3333"
✓ Answer: null
✓ Confidence: 0.0
✓ Reason: "Phone number found, but for different person (John Doe, not Sarah Klein)"
Note: Entity match is CRITICAL!

✅ Example 6 - Date Format:
Question: "When did the accident occur?"
Chunk: "Date of Incident: January 24, 2024"
✓ Answer: "January 24, 2024"
✓ Confidence: 0.95
✓ Reason: "Date explicitly stated"
Note: Keep original format, don't convert!

❌ Example 7 - Requires Inference (DON'T):
Question: "Is the damage severe?"
Chunk: "Front bumper cracked, hood dented, headlight broken"
✓ Answer: null
✓ Confidence: 0.0
✓ Reason: "Question requires subjective judgment. Chunk describes damage but doesn't explicitly state severity level."
Note: "Severe" is interpretation, not a stated fact!
Confidence: 0.95
Sources: ["chunk_123"]
Reason: "Found explicitly in chunk_123"

Example 2 - Answer NOT Found:
Question: "What is the claimant's email address?"
Chunk: "Claimant contact: John Doe, phone: 555-1234"
Answer: null
Confidence: 0.0
Sources: []
Reason: "Email address not mentioned in any retrieved chunk"

Example 3 - Multiple Chunks:
Question: "When did the accident occur?"
Chunk 1: "Report filed on 2024-01-15"
Chunk 2: "Accident occurred on 2024-01-10 at 3:00 PM"
Answer: "2024-01-10 at 3:00 PM"
Confidence: 0.95
Sources: ["chunk_456"]
Reason: "Found explicitly in chunk_456"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RETRIEVED CHUNKS
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

Extract the answer from the chunks above. If not found, return null.
"""
        
        return ChatPromptTemplate.from_template(template)
    
    def answer(self, question: str, retriever) -> Dict[str, Any]:
        """
        Answer a needle question using retrieved atomic facts.
        
        This is the main public method of the Needle Agent.
        
        Args:
            question: User's needle question (e.g., "What is the claim number?")
            retriever: Pre-built retriever from Index Layer
                      Must have .retrieve(question) method
                      Returns list of NodeWithScore objects
        
        Returns:
            Dictionary with:
                - answer: str or None (the extracted fact)
                - confidence: float (0.0 to 1.0)
                - sources: list of chunk IDs used
                - reason: str (explanation)
        
        WHY THIS METHOD:
        - Single responsibility: extract one fact
        - Retriever is injected (dependency injection)
        - No side effects (pure function)
        - Deterministic (temperature=0.0)
        - Structured output (validated)
        
        WHY RETRIEVER IS INJECTED:
        - Retriever is built by Index Layer
        - Retriever encapsulates embedding model, FAISS, threshold
        - Agent doesn't know about vector search internals
        - Clean separation of concerns
        - Easy to test with mock retriever
        """
        if not question or not question.strip():
            raise ValueError("Question cannot be empty")
        
        # Step 1: Retrieve atomic chunks
        # WHY: Retriever already filters by similarity and returns ONLY relevant chunks
        # WHY: Retriever returns NodeWithScore objects from LlamaIndex
        print(f"\n🔍 Retrieving chunks for: '{question}'")
        retrieved_nodes = retriever.retrieve(question.strip())
        
        # Step 2: Check if any chunks were retrieved
        # WHY: If retriever returns nothing, no fact can be extracted
        if not retrieved_nodes or len(retrieved_nodes) == 0:
            print("   ⚠️  No chunks retrieved (below similarity threshold)")
            return {
                "answer": None,
                "confidence": 0.0,
                "sources": [],
                "retrieved_chunks_content": [],  # No chunks retrieved
                "reason": "No relevant chunks found above similarity threshold"
            }
        
        print(f"   ✅ Retrieved {len(retrieved_nodes)} chunk(s)")
        
        # Step 3: Format chunks for LLM
        # WHY: LLM needs text content and chunk IDs for traceability
        # WHY: Each chunk is formatted with ID and text
        chunks_text = ""
        chunk_ids = []
        chunk_contents = []  # Store actual content for evaluation
        
        for i, node in enumerate(retrieved_nodes, 1):
            chunk_id = node.node.node_id  # LlamaIndex node ID
            chunk_text = node.node.text    # Actual text content
            chunk_score = node.score       # Similarity score
            
            chunks_text += f"\n[Chunk {i}] ID: {chunk_id}\n"
            chunks_text += f"Similarity: {chunk_score:.3f}\n"
            chunks_text += f"Content: {chunk_text}\n"
            chunks_text += "─" * 60 + "\n"
            
            chunk_ids.append(chunk_id)
            chunk_contents.append(chunk_text)  # Save for evaluation
        
        # Step 4: Format prompt with question and chunks
        # WHY: Combines template with specific question and retrieved text
        formatted_prompt = self.prompt.format_messages(
            question=question.strip(),
            chunks=chunks_text,
            format_instructions=self.parser.get_format_instructions()
        )
        
        # Convert to message format for tool calling
        messages = [{"role": msg.type, "content": msg.content} for msg in formatted_prompt]
        
        # Step 5: Get LLM response (with optional MCP tools)
        # WHY: LLM extracts the atomic fact from chunks
        # WHY: Temperature=0.0 ensures deterministic extraction
        # WHY: Tools enabled: LLM can delegate date calculations to MCP
        print(f"   🤖 Extracting fact with {self.model}...")
        
        if self.enable_mcp_tools:
            print(f"   🔧 MCP tools enabled - LLM can use tools if needed")
            response = self.llm.invoke(
                messages,
                tools=self.tools,
                tool_choice="auto"  # LLM decides when to use tools
            )
            
            # Handle tool calls if LLM decided to use them
            if hasattr(response, 'tool_calls') and response.tool_calls:
                return self._handle_tool_call(response, messages, chunk_contents, chunk_ids)
        else:
            response = self.llm.invoke(messages)
        
        # Step 6: Parse structured output (no tools used)
        # WHY: Validates response matches NeedleAnswer schema
        # WHY: Handles null answers gracefully
        content = response.content if isinstance(response.content, str) else str(response.content)
        result: NeedleAnswer = self.parser.parse(content)
        
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
        chunk_contents: List[str],
        chunk_ids: Optional[List[str]] = None
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
            chunk_ids: List of chunk IDs (for fallback handling)
        
        Returns:
            Final answer dictionary
        """
        print(f"   🔧 LLM called MCP tool for date calculation")
        
        for tool_call in response.tool_calls:
            # Debug: Print tool call structure
            print(f"      Debug - tool_call type: {type(tool_call)}")
            print(f"      Debug - tool_call: {tool_call}")
            
            # Handle both dict and object formats
            if isinstance(tool_call, dict):
                tool_name = tool_call['name']
                tool_args = tool_call['args']
                tool_id = tool_call['id']
            else:
                # If it's an object, access as attributes
                tool_name = tool_call.name
                tool_args = tool_call.args
                tool_id = tool_call.id
            
            print(f"      Tool name: {tool_name}")
            print(f"      Tool args: {tool_args}")
            print(f"      Tool ID: {tool_id}")
            
            if tool_name == 'calculate_days_between':
                try:
                    # Execute the MCP tool
                    # WHY: Provides exact, deterministic date arithmetic
                    start = tool_args.get('start_date') if isinstance(tool_args, dict) else getattr(tool_args, 'start_date', None)
                    end = tool_args.get('end_date') if isinstance(tool_args, dict) else getattr(tool_args, 'end_date', None)
                    
                    if not start or not end:
                        raise ValueError(f"Missing date arguments: start={start}, end={end}")
                    
                    print(f"      Calculating: {start} to {end}")
                    tool_result = calculate_days_between(start, end)
                    
                    # Debug: Print the tool result structure
                    print(f"      Tool result type: {type(tool_result)}")
                    print(f"      Tool result: {tool_result}")
                    
                    # Safely access the result
                    if isinstance(tool_result, dict) and 'number_of_days' in tool_result:
                        print(f"      Result: {tool_result['number_of_days']} days")
                    else:
                        print(f"      ⚠️  Unexpected tool result format")
                        
                except Exception as e:
                    print(f"      ❌ Error executing MCP tool: {e}")
                    import traceback
                    traceback.print_exc()
                    
                    # Return error result
                    return {
                        "answer": None,
                        "confidence": 0.0,
                        "sources": chunk_ids if chunk_ids else [],
                        "retrieved_chunks_content": chunk_contents,
                        "reason": f"MCP tool execution failed: {str(e)}"
                    }
                
                # Send tool result back to LLM
                # Format tool call properly for OpenAI
                if isinstance(tool_call, dict):
                    tool_call_dict = tool_call
                else:
                    tool_call_dict = {
                        "name": tool_name,
                        "args": tool_args,
                        "id": tool_id,
                        "type": "function"
                    }
                
                messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [tool_call_dict]
                })
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_id,
                    "name": tool_name,
                    "content": json.dumps(tool_result)
                })
                
                print(f"      Sending tool result back to LLM...")
                
                # Get final answer from LLM
                print(f"   🤖 LLM formatting answer with tool result...")
                final_response = self.llm.invoke(messages)
                
                # Parse the final answer
                content = final_response.content if isinstance(final_response.content, str) else str(final_response.content)
                
                try:
                    result: NeedleAnswer = self.parser.parse(content)
                except Exception as e:
                    # If parsing fails, the LLM might have returned plain text
                    # Extract the answer directly from tool result
                    print(f"      ⚠️  LLM response parsing failed: {e}")
                    print(f"      Using tool result directly...")
                    
                    days_raw = tool_result.get('number_of_days', 0)
                    days = int(days_raw) if isinstance(days_raw, (int, float, str)) else 0
                    answer = f"{abs(days)} days" if days >= 0 else f"{abs(days)} days (reverse order)"
                    
                    return {
                        "answer": answer,
                        "confidence": 0.95,
                        "sources": chunk_ids if chunk_ids else [],
                        "retrieved_chunks_content": chunk_contents,
                        "reason": f"Date difference calculated using MCP tool: {start} to {end}"
                    }
                
                return {
                    "answer": result.answer,
                    "confidence": result.confidence,
                    "sources": result.sources,
                    "retrieved_chunks_content": chunk_contents,
                    "reason": result.reason + " (Used MCP: calculate_days_between)"
                }
        
        # Fallback if tool call failed
        return {
            "answer": None,
            "confidence": 0.0,
            "sources": [],
            "retrieved_chunks_content": chunk_contents,
            "reason": "Tool call failed"
        }


# ====================================================
# FACTORY FUNCTION - Clean interface
# ====================================================

def create_needle_agent(
    model: str = "gpt-4o-mini",
    temperature: float = 0.0,
    enable_mcp_tools: bool = True,
) -> NeedleAgent:
    """
    Factory function to create a Needle Agent.
    
    WHY: Provides clean interface for importing and using this agent.
    
    Args:
        model: OpenAI model name
        temperature: LLM temperature (0.0 = deterministic)
        enable_mcp_tools: Enable MCP tools for date calculations (default: True)
    
    Returns:
        Configured NeedleAgent instance
    """
    return NeedleAgent(
        model=model,
        temperature=temperature,
        enable_mcp_tools=enable_mcp_tools,
    )

