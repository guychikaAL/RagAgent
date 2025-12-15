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
    
    def answer(self, question: str, retriever=None, query_engine=None) -> Dict[str, Any]:
        """
        Answer a summary question using MapReduce or simple retrieval.
        
        Args:
            question: User's summary question
            retriever: Pre-built Summary Retriever (legacy mode)
            query_engine: MapReduce Query Engine (recommended)
            
        Returns:
            Dict with answer, confidence, sources, reason
        """
        if not question or not question.strip():
            raise ValueError("Question cannot be empty")
        
        if retriever is None and query_engine is None:
            raise ValueError("Must provide either retriever or query_engine")
        
        # PREFERRED: Use MapReduce if provided
        if query_engine is not None:
            return self._answer_with_map_reduce(question, query_engine)
        
        # FALLBACK: Use simple retrieval
        return self._answer_with_retriever(question, retriever)
    
    def _answer_with_map_reduce(self, question: str, query_engine) -> Dict[str, Any]:
        """Answer using MapReduce (tree_summarize)."""
        print(f"\n🗺️  Using MAP-REDUCE for comprehensive summarization...")
        print(f"   Question: '{question}'")
        
        # Query the MapReduce engine
        response = query_engine.query(question.strip())
        
        # Extract answer
        answer_text = str(response)
        
        # Get source nodes (these are the chunks that went through MAP step)
        source_nodes = getattr(response, 'source_nodes', [])
        chunk_ids = [node.node_id for node in source_nodes]
        chunk_contents = [node.text for node in source_nodes]
        
        print(f"   ✅ Generated summary using {len(chunk_ids)} chunk(s)")
        
        # Create map-reduce visualization data
        map_reduce_steps = {
            "total_chunks": len(chunk_ids),
            "map_inputs": [
                {
                    "chunk_id": chunk_ids[i][:16] + "..." if len(chunk_ids[i]) > 16 else chunk_ids[i],
                    "chunk_preview": chunk_contents[i][:150] + "..." if len(chunk_contents[i]) > 150 else chunk_contents[i],
                    "chunk_number": i + 1
                }
                for i in range(min(len(chunk_ids), 10))  # Show first 10 for visualization
            ],
            "reduce_description": f"Hierarchically combined {len(chunk_ids)} summaries → Final answer",
            "process": [
                f"MAP: {len(chunk_ids)} chunks → {len(chunk_ids)} individual summaries",
                f"REDUCE Level 1: {len(chunk_ids)} → ~{len(chunk_ids)//3} combined summaries",
                f"REDUCE Level 2: ~{len(chunk_ids)//3} → ~{len(chunk_ids)//9 or 1} final summaries",
                "FINAL: Comprehensive synthesized answer"
            ]
        }
        
        return {
            "answer": answer_text,
            "confidence": 0.85,
            "sources": chunk_ids,
            "retrieved_chunks_content": chunk_contents,
            "reason": f"MapReduce hierarchical summarization of {len(chunk_ids)} chunks",
            "map_reduce_steps": map_reduce_steps  # For GUI visualization
        }
    
    def _answer_with_retriever(self, question: str, retriever) -> Dict[str, Any]:
        """Answer using simple retrieval + synthesis."""
        print(f"\n📚 Retrieving context for: '{question}'")
        
        # Retrieve chunks
        retrieved_nodes = retriever.retrieve(question.strip())
        
        if not retrieved_nodes or len(retrieved_nodes) == 0:
            print("   ⚠️  No chunks retrieved")
            return {
                "answer": "No relevant information found.",
                "confidence": 0.0,
                "sources": [],
                "retrieved_chunks_content": [],
                "reason": "No chunks retrieved"
            }
        
        print(f"   ✅ Retrieved {len(retrieved_nodes)} chunk(s)")
        
        # Extract content and IDs
        chunk_contents = []
        chunk_ids = []
        for node in retrieved_nodes:
            chunk_contents.append(node.node.text)
            chunk_id = node.node.metadata.get('chunk_id', node.node.node_id)
            chunk_ids.append(chunk_id)
        
        # Combine context
        context = "\n\n".join([
            f"[Chunk {i+1}]\n{content}"
            for i, content in enumerate(chunk_contents)
        ])
        
        # Synthesize
        result = self.synthesize(question, context, len(chunk_ids))
        
        # Add chunk contents for evaluation
        result["sources"] = chunk_ids
        result["retrieved_chunks_content"] = chunk_contents
        
        return result
    
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
