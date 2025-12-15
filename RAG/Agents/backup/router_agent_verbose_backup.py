"""
====================================================
ROUTER AGENT - CLASSIFICATION ONLY
====================================================

RESPONSIBILITY:
This agent classifies user questions into retrieval routes.
It does NOT retrieve data.
It does NOT generate answers.
It ONLY decides: NEEDLE or SUMMARY.

WHY THIS EXISTS:
- Different question types need different retrieval strategies
- Needle questions: precise, atomic fact lookup (high precision)
- Summary questions: broad, contextual gathering (high recall)
- Routing BEFORE retrieval optimizes both cost and quality

WHY LANGCHAIN:
- LangChain excels at LLM orchestration and structured outputs
- LlamaIndex is for retrieval (used in downstream agents)
- Clear separation: routing (LangChain) vs retrieval (LlamaIndex)

WHY NO RETRIEVAL HERE:
- Routing is classification, not data access
- Router has no knowledge of claim data
- Router decides WHERE to go, not WHAT to return
- Keeps agent focused and testable

CRITICAL RULES:
- NEVER access FAISS
- NEVER call retrievers
- NEVER use embeddings
- NEVER generate final answers
- ONLY return classification result

====================================================
"""

import os
from typing import Dict, Any
from pydantic import BaseModel, Field

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser


# ====================================================
# OUTPUT SCHEMA - Enforces structured response
# ====================================================

class RouteDecision(BaseModel):
    """
    Structured output for routing decision.
    
    WHY PYDANTIC:
    - Enforces exact schema
    - Automatic validation
    - Type safety
    - No free-form text leakage
    """
    route: str = Field(
        description="Must be exactly 'needle' or 'summary'",
        pattern="^(needle|summary)$"
    )
    confidence: float = Field(
        description="Confidence score between 0.0 and 1.0",
        ge=0.0,
        le=1.0
    )
    reason: str = Field(
        description="Brief explanation (1-2 sentences) for the routing decision"
    )


# ====================================================
# ROUTER AGENT - Classification Only
# ====================================================

class RouterAgent:
    """
    Production-grade question classifier for RAG routing.
    
    Routes questions to appropriate retrieval strategy:
    - NEEDLE: Precise fact lookup (child chunks, high threshold)
    - SUMMARY: Contextual gathering (parent+child chunks, no threshold)
    
    WHY THIS AGENT:
    - Optimizes retrieval before it happens
    - Different questions need different strategies
    - Prevents over-retrieval (costly) or under-retrieval (incomplete)
    
    WHY SEPARATE FROM RETRIEVAL:
    - Classification is pure logic (LLM reasoning)
    - Retrieval is data access (vector search)
    - Testing routing without touching data
    - Can swap retrieval implementation without changing routing
    
    ARCHITECTURE:
    - Uses ChatOpenAI for classification
    - Structured output (Pydantic)
    - Zero temperature (deterministic)
    - Explicit prompt constraints
    """
    
    def __init__(
        self,
        model: str = "gpt-4o-mini",
        temperature: float = 0.0,
    ):
        """
        Initialize the Router Agent.
        
        Args:
            model: OpenAI model for classification
                   (gpt-4o-mini is fast and cheap for classification)
            temperature: LLM temperature (0.0 = deterministic)
        
        WHY THESE DEFAULTS:
        - gpt-4o-mini: Fast, cheap, sufficient for classification
        - temperature=0.0: Routing must be consistent and deterministic
        """
        # Validate OpenAI API key
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError(
                "OPENAI_API_KEY not found. "
                "Set it in environment or .env file."
            )
        
        self.model = model
        self.temperature = temperature
        
        # Initialize LLM
        # WHY: ChatOpenAI provides consistent, structured outputs
        self.llm = ChatOpenAI(
            model=self.model,
            temperature=self.temperature,
        )
        
        # Initialize output parser
        # WHY: Enforces structured response, prevents free-form text
        self.parser = PydanticOutputParser(pydantic_object=RouteDecision)
        
        # Build prompt
        # WHY: Prompt design is critical for correct classification
        self.prompt = self._build_prompt()
        
        print(f"✅ Router Agent initialized")
        print(f"   Model: {self.model}")
        print(f"   Temperature: {self.temperature}")
        print(f"   Output: Structured (Pydantic)")
    
    def _build_prompt(self) -> ChatPromptTemplate:
        """
        Build the routing classification prompt.
        
        WHY THIS PROMPT STRUCTURE:
        - Explicit role definition (classifier, not answerer)
        - Clear definitions of needle vs summary
        - Examples for few-shot learning
        - Format instructions for structured output
        - Explicit constraints (never answer the question)
        
        Returns:
            ChatPromptTemplate for routing classification
        """
        template = """You are a ROUTING CLASSIFIER for a RAG system.

Your ONLY job is to classify questions into one of two retrieval routes:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ROUTE 1: NEEDLE (Precise Fact Lookup)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Use NEEDLE when the question asks for:
✓ ONE specific atomic fact (name, number, date, amount, identifier)
✓ A single entity attribute (person's phone, vehicle VIN, policy number)
✓ Date arithmetic between TWO specific dates
✓ Existence checks ("Is there a...", "Does X have Y?")
✓ Binary questions answerable with yes/no + fact
✓ Questions starting with: "what is", "who is", "when did", "how much was", "which"

✅ NEEDLE Examples (Clear Cases):
✓ "What is Jon Mor's phone number?" → Single fact
✓ "When did the accident occur?" → Single date
✓ "What is the vehicle VIN?" → Single identifier
✓ "How much was the repair estimate?" → Single amount
✓ "Who filed claim #5?" → Single name
✓ "What color was the vehicle?" → Single attribute
✓ "Is there damage to the front bumper?" → Binary + fact
✓ "How many days between Jan 15 and Feb 20?" → Date calc (2 dates)

❌ NEEDLE Counter-Examples (Should be SUMMARY):
✗ "What vehicles are in the document?" → Multiple entities (SUMMARY)
✗ "How many claims involve Honda vehicles?" → Aggregate count (SUMMARY)
✗ "What damage was reported?" → Multiple facts (SUMMARY)
✗ "Compare claims #1 and #5" → Multiple claims (SUMMARY)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ROUTE 2: SUMMARY (Comprehensive Context)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Use SUMMARY when the question asks for:
✓ Explanations, narratives, or event descriptions
✓ Multiple related facts that need synthesis
✓ Comparisons between entities (claims, people, events)
✓ Document-level aggregates (counts, totals, lists of ALL X)
✓ Patterns or trends across multiple instances
✓ Contextual analysis requiring broad view
✓ "Why" or "how" questions needing interpretation
✓ Questions starting with: "describe", "explain", "summarize", "list all", "how many [entities]", "compare"

✅ SUMMARY Examples (Clear Cases):
✓ "Summarize the accident." → Narrative synthesis
✓ "Describe what happened." → Multi-fact description
✓ "Explain the damages." → Contextual explanation
✓ "What led to this claim?" → Causal analysis
✓ "How many claims are in the document?" → Document-level count
✓ "List all claimants." → Comprehensive enumeration
✓ "What vehicles are mentioned?" → Multiple entities
✓ "Compare claims #1 and #5." → Multi-entity comparison
✓ "What patterns do you see in the accidents?" → Trend analysis
✓ "Which claims involve rear-end collisions?" → Filtering + listing
✓ "How many people are involved across all claims?" → Cross-claim aggregate

❌ SUMMARY Counter-Examples (Should be NEEDLE):
✗ "What is the claim number?" → Single fact (NEEDLE)
✗ "When did John's accident occur?" → Single date (NEEDLE)
✗ "How much damage to vehicle #3?" → Single amount (NEEDLE)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CLASSIFICATION DECISION TREE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Follow this decision logic IN ORDER:

1️⃣  Does question ask for date arithmetic? (e.g., "days between X and Y")
    → YES: NEEDLE (requires MCP date calculation tool)
    
2️⃣  Does question ask about MULTIPLE entities or ALL of something?
    (e.g., "all claims", "list claimants", "which claims", "compare X and Y")
    → YES: SUMMARY (needs full document scan)
    
3️⃣  Does question ask for document-level COUNT or TOTAL?
    (e.g., "how many claims", "total forms", "count all")
    → YES: SUMMARY (needs high recall to count everything)
    
4️⃣  Does question ask for ONE SPECIFIC fact about ONE SPECIFIC entity?
    (e.g., "Jon's phone", "claim #5 date", "VIN number")
    → YES: NEEDLE (precise fact lookup)
    
5️⃣  Does question need explanation, description, or synthesis?
    (e.g., "explain", "describe", "what happened", "why")
    → YES: SUMMARY (needs contextual understanding)
    
6️⃣  Does question have comparison/analysis/pattern words?
    (e.g., "compare", "similar", "pattern", "trend", "relationship")
    → YES: SUMMARY (needs broad context)
    
7️⃣  If uncertain or ambiguous:
    → DEFAULT: SUMMARY (safer, more complete answers)

SPECIAL CASE - Date Calculations:
Questions like "How many days between X and Y?" should go to NEEDLE because:
- They require extracting TWO atomic facts (two dates)
- Needle Agent has MCP tools for precise date arithmetic
- Summary Agent cannot perform deterministic calculations

SPECIAL CASE - Aggregate/Count Questions:
Questions like "How many claims are in the document?" should go to SUMMARY because:
- They require seeing the ENTIRE document structure (not just a few chunks)
- They need high recall to count ALL entities across the document
- Needle Agent only sees 3-5 chunks and will undercount
- Examples: "total claims", "how many forms", "count all claimants", "list all claims"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONFIDENCE SCORING GUIDELINES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Assign confidence based on classification certainty:

🟢 HIGH CONFIDENCE (0.85-0.95):
- Question clearly matches one route's patterns
- Uses explicit keywords from route definition
- No ambiguity about single vs multiple facts
Examples: "What is X?", "How many days between...", "List all..."

🟡 MEDIUM CONFIDENCE (0.70-0.84):
- Question could reasonably fit either route
- Contains mixed signals (specific fact but needs context)
- Slightly ambiguous scope
Examples: "What damage was reported?", "Who was involved?"

🔴 LOW CONFIDENCE (0.50-0.69):
- Highly ambiguous question
- Could be interpreted multiple ways
- Unusual phrasing or unclear intent
Examples: "Tell me about it", "What should I know?", "Anything important?"

Note: If confidence < 0.70, default to SUMMARY (safer, more complete).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CRITICAL CONSTRAINTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️  DO NOT attempt to answer the question
⚠️  DO NOT retrieve any data
⚠️  DO NOT make up information
⚠️  ONLY classify the question type

You are a router, not a retriever or answerer.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT FORMAT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{format_instructions}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
QUESTION TO CLASSIFY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{question}

Classify this question as NEEDLE or SUMMARY and provide your reasoning.
"""
        
        return ChatPromptTemplate.from_template(template)
    
    def route(self, question: str) -> Dict[str, Any]:
        """
        Classify a question into a retrieval route.
        
        This is the main public method of the Router Agent.
        
        Args:
            question: User's question string
        
        Returns:
            Dictionary with:
                - route: "needle" or "summary"
                - confidence: float between 0.0 and 1.0
                - reason: string explanation
        
        WHY THIS METHOD:
        - Single responsibility: classify question
        - No side effects (pure function)
        - Deterministic (temperature=0.0)
        - Structured output (validated)
        
        WHY NO RETRIEVAL:
        - Router doesn't know about claims or data
        - Router only knows question patterns
        - Retrieval happens in downstream agents
        - Separation of concerns
        """
        if not question or not question.strip():
            raise ValueError("Question cannot be empty")
        
        # Format prompt with question and output instructions
        # WHY: Combines template with specific question and schema
        formatted_prompt = self.prompt.format_messages(
            question=question.strip(),
            format_instructions=self.parser.get_format_instructions()
        )
        
        # Get LLM response
        # WHY: LLM classifies based on question patterns
        response = self.llm.invoke(formatted_prompt)
        
        # Parse structured output
        # WHY: Validates response matches RouteDecision schema
        content = response.content if isinstance(response.content, str) else str(response.content)
        decision: RouteDecision = self.parser.parse(content)
        
        # Convert to dictionary
        # WHY: Standard Python dict for easy JSON serialization
        return {
            "route": decision.route,
            "confidence": decision.confidence,
            "reason": decision.reason
        }
    
    def route_batch(self, questions: list[str]) -> list[Dict[str, Any]]:
        """
        Route multiple questions in batch.
        
        Args:
            questions: List of question strings
        
        Returns:
            List of routing decisions (one per question)
        
        WHY THIS METHOD:
        - Batch processing for efficiency
        - Useful for testing and analysis
        - Maintains order of questions
        """
        return [self.route(q) for q in questions]


# ====================================================
# FACTORY FUNCTION - Clean interface
# ====================================================

def create_router_agent(
    model: str = "gpt-4o-mini",
    temperature: float = 0.0,
) -> RouterAgent:
    """
    Factory function to create a Router Agent.
    
    WHY: Provides clean interface for importing and using this agent.
    
    Args:
        model: OpenAI model name
        temperature: LLM temperature (0.0 = deterministic)
    
    Returns:
        Configured RouterAgent instance
    """
    return RouterAgent(
        model=model,
        temperature=temperature,
    )

