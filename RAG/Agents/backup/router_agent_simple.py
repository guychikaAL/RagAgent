"""
Router Agent - Simple & Concise Version
Classifies questions as NEEDLE (precise fact) or SUMMARY (broad context)
"""

import os
from typing import Dict, Any
from pydantic import BaseModel, Field

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser


class RouteDecision(BaseModel):
    """Structured routing decision"""
    route: str = Field(description="Must be 'needle' or 'summary'", pattern="^(needle|summary)$")
    confidence: float = Field(description="Confidence 0.0-1.0", ge=0.0, le=1.0)
    reason: str = Field(description="Brief explanation")


class RouterAgent:
    """
    Simple question classifier for RAG routing.
    - NEEDLE: Single fact lookup (phone number, date, name)
    - SUMMARY: Multiple facts or explanations (summaries, comparisons)
    """
    
    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.0):
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY not found")
        
        self.model = model
        self.temperature = temperature
        self.llm = ChatOpenAI(model=self.model, temperature=self.temperature)
        self.parser = PydanticOutputParser(pydantic_object=RouteDecision)
        self.prompt = self._build_prompt()
        
        print(f"✅ Router Agent initialized")
        print(f"   Model: {self.model}")
        print(f"   Temperature: {self.temperature}")
        print(f"   Output: Structured (Pydantic)")
    
    def _build_prompt(self) -> ChatPromptTemplate:
        """Build routing prompt - concise version"""
        template = """You are a routing classifier for a RAG system.

Classify questions into ONE of two routes:

**ROUTE: NEEDLE** (Precise fact lookup)
Use when asking for:
- Single specific fact (name, number, date, phone, VIN, amount)
- One entity attribute
- Date arithmetic (e.g., "days between X and Y")

Examples:
✓ "What is Jon Mor's phone number?"
✓ "When did the accident occur?"
✓ "How much was the repair cost?"
✓ "How many days between Jan 15 and Feb 20?"

**ROUTE: SUMMARY** (Broad context)
Use when asking for:
- Explanations or descriptions
- Multiple facts needing synthesis
- Document-level aggregates/counts ("how many claims")
- Comparisons or lists
- "What happened" or "describe" questions

Examples:
✓ "Summarize the claim"
✓ "What happened in the accident?"
✓ "List all claimants"
✓ "How many claims are in the document?"
✓ "Compare claims #1 and #5"

**Key Rule:** 
- One specific fact = NEEDLE
- Multiple facts or explanation = SUMMARY
- Document-level count ("how many claims") = SUMMARY
- Date calculation = NEEDLE

Question: {question}

{format_instructions}

Respond with valid JSON only."""

        return ChatPromptTemplate.from_template(template).partial(
            format_instructions=self.parser.get_format_instructions()
        )
    
    def classify(self, question: str) -> Dict[str, Any]:
        """
        Classify a question into needle or summary route.
        
        Args:
            question: User's question
            
        Returns:
            Dict with route, confidence, reason
        """
        if not question or not question.strip():
            raise ValueError("Question cannot be empty")
        
        # Generate classification
        chain = self.prompt | self.llm | self.parser
        result: RouteDecision = chain.invoke({"question": question})
        
        return {
            "route": result.route,
            "confidence": result.confidence,
            "reason": result.reason,
        }
