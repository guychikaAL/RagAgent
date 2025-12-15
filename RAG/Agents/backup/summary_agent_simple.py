"""
Summary Agent - Simple & Concise Version
Synthesizes comprehensive answers from multiple chunks
"""

import os
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser


class SummaryAnswer(BaseModel):
    """Structured summary result"""
    answer: str = Field(description="Comprehensive synthesized answer")
    confidence: float = Field(description="Confidence 0.0-1.0", ge=0.0, le=1.0)
    sources: int = Field(description="Number of chunks used")
    reason: str = Field(description="Brief explanation")


class SummaryAgent:
    """
    Simple context synthesizer.
    - Combine multiple facts
    - Provide comprehensive answers
    - Ground answers in retrieved context
    """
    
    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.2, enable_mcp_tools: bool = True):
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY not found")
        
        self.model = model
        self.temperature = temperature
        self.enable_mcp_tools = enable_mcp_tools
        
        self.llm = ChatOpenAI(model=self.model, temperature=self.temperature)
        self.parser = PydanticOutputParser(pydantic_object=SummaryAnswer)
        self.prompt = self._build_prompt()
        
        print(f"✅ Summary Agent initialized")
        print(f"   Model: {self.model}")
        print(f"   Temperature: {self.temperature}")
        print(f"   Output: Structured (Pydantic)")
        print(f"   Policy: CONTEXT-GROUNDED SYNTHESIS")
        print(f"   MCP Tools: {'✅ Enabled' if self.enable_mcp_tools else '❌ Disabled'}")
    
    def _build_prompt(self) -> ChatPromptTemplate:
        """Build synthesis prompt - concise version"""
        system_template = """You are a CONTEXT SYNTHESIZER.

**Your Task:**
Synthesize a comprehensive answer from the provided chunks.

**Rules:**
1. Use information from ALL relevant chunks
2. Combine facts into a coherent narrative
3. Stay grounded in the context - don't add external knowledge
4. If information is missing, state it clearly
5. For count questions ("how many claims"), scan ALL chunks carefully

**Answer Quality:**
- Be complete and well-structured
- Combine related facts logically
- Use specific details from chunks
- Be transparent about gaps or uncertainties

{format_instructions}"""

        user_template = """Question: {question}

Context (from {num_chunks} chunks):
{context}

Synthesize a comprehensive answer. Respond with valid JSON only."""

        messages = [
            ("system", system_template),
            ("human", user_template)
        ]
        
        return ChatPromptTemplate.from_messages(messages).partial(
            format_instructions=self.parser.get_format_instructions()
        )
    
    def synthesize(
        self,
        question: str,
        context: str,
        num_sources: int
    ) -> Dict[str, Any]:
        """
        Synthesize answer from context.
        
        Args:
            question: User's question
            context: Combined context from MapReduce
            num_sources: Number of chunks used
            
        Returns:
            Dict with answer, confidence, sources, reason
        """
        if not question or not question.strip():
            raise ValueError("Question cannot be empty")
        
        if not context or not context.strip():
            return {
                "answer": "No context available to answer the question.",
                "confidence": 0.0,
                "sources": 0,
                "reason": "No context provided"
            }
        
        # Generate synthesis
        print(f"   🤖 Synthesizing answer with {self.model}...")
        
        messages = self.prompt.format_messages(
            question=question,
            context=context,
            num_chunks=num_sources
        )
        
        response = self.llm.invoke(messages)
        content = response.content if isinstance(response.content, str) else str(response.content)
        
        try:
            result: SummaryAnswer = self.parser.parse(content)
        except Exception as e:
            print(f"      ⚠️  Parsing failed: {e}")
            # Fallback: return raw content
            return {
                "answer": content,
                "confidence": 0.7,
                "sources": num_sources,
                "reason": f"Synthesis complete (parsing failed: {str(e)})"
            }
        
        return {
            "answer": result.answer,
            "confidence": result.confidence,
            "sources": num_sources,
            "reason": result.reason,
        }
