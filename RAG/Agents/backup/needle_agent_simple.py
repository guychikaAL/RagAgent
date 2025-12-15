"""
Needle Agent - Simple & Concise Version
Extracts precise atomic facts from retrieved chunks
"""

import os
import json
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from llama_index.core.schema import NodeWithScore

# Import MCP tools
from mcp_tools import calculate_days_between


class NeedleAnswer(BaseModel):
    """Structured needle extraction result"""
    answer: Optional[str] = Field(description="The extracted fact or None if not found")
    confidence: float = Field(description="Confidence 0.0-1.0", ge=0.0, le=1.0)
    sources: List[str] = Field(description="List of chunk IDs used")
    reason: str = Field(description="Brief explanation")


class NeedleAgent:
    """
    Simple precise fact extractor.
    - NO guessing or hallucination
    - Extract ONLY what's explicitly stated
    - Use MCP tools for date calculations
    """
    
    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.0, enable_mcp_tools: bool = True):
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY not found")
        
        self.model = model
        self.temperature = temperature
        self.enable_mcp_tools = enable_mcp_tools
        
        # Initialize LLM with optional tool binding
        self.llm = ChatOpenAI(model=self.model, temperature=self.temperature)
        
        if self.enable_mcp_tools:
            # Bind MCP date calculation tool
            tools = [{
                "type": "function",
                "function": {
                    "name": "calculate_days_between",
                    "description": "Calculate exact number of days between two dates. Use for date arithmetic questions.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "start_date": {
                                "type": "string",
                                "description": "Start date in YYYY-MM-DD format (e.g., '2024-01-15')"
                            },
                            "end_date": {
                                "type": "string",
                                "description": "End date in YYYY-MM-DD format (e.g., '2024-02-20')"
                            }
                        },
                        "required": ["start_date", "end_date"]
                    }
                }
            }]
            self.llm = self.llm.bind_tools(tools)
        
        self.parser = PydanticOutputParser(pydantic_object=NeedleAnswer)
        self.prompt = self._build_prompt()
        
        print(f"✅ Needle Agent initialized")
        print(f"   Model: {self.model}")
        print(f"   Temperature: {self.temperature}")
        print(f"   Output: Structured (Pydantic)")
        print(f"   Policy: NO GUESSING")
        print(f"   MCP Tools: {'✅ Enabled' if self.enable_mcp_tools else '❌ Disabled'}")
    
    def _build_prompt(self) -> ChatPromptTemplate:
        """Build extraction prompt - concise version"""
        system_template = """You are a PRECISE FACT EXTRACTOR.

**CRITICAL RULES:**
1. Extract ONLY facts explicitly stated in the provided chunks
2. NEVER guess, infer, or use external knowledge
3. If the fact is not found, answer with None
4. Be EXACT - copy numbers, names, dates as written

**For Date Arithmetic Questions:**
If the question asks "how many days between X and Y":
1. Find BOTH dates in the chunks
2. Convert to YYYY-MM-DD format
3. Call the calculate_days_between tool
4. Return the exact result

**Examples:**
✓ Found in chunk: "Phone: (555) 123-4567" → Answer: "(555) 123-4567"
✓ Found in chunk: "Accident: 2024-01-15, Repair: 2024-02-20" → Call tool, answer: "36 days"
✗ Not found → Answer: None

{format_instructions}"""

        user_template = """Question: {question}

Retrieved Chunks:
{chunks}

Extract the fact. Respond with valid JSON only."""

        messages = [
            ("system", system_template),
            ("human", user_template)
        ]
        
        return ChatPromptTemplate.from_messages(messages).partial(
            format_instructions=self.parser.get_format_instructions()
        )
    
    def extract(
        self,
        question: str,
        retrieved_nodes: List[NodeWithScore]
    ) -> Dict[str, Any]:
        """
        Extract a precise fact from retrieved chunks.
        
        Args:
            question: User's question
            retrieved_nodes: Retrieved chunks from vector index
            
        Returns:
            Dict with answer, confidence, sources, reason
        """
        if not question or not question.strip():
            raise ValueError("Question cannot be empty")
        
        if not retrieved_nodes:
            return {
                "answer": None,
                "confidence": 0.0,
                "sources": [],
                "retrieved_chunks_content": [],
                "reason": "No chunks retrieved"
            }
        
        # Extract chunk contents and IDs
        chunk_contents = []
        chunk_ids = []
        for node in retrieved_nodes:
            chunk_contents.append(node.node.text)
            chunk_id = node.node.metadata.get('chunk_id', 'unknown')
            chunk_ids.append(chunk_id)
        
        # Format chunks for prompt
        chunks_text = "\n\n".join([
            f"[Chunk {i+1}]\n{content}"
            for i, content in enumerate(chunk_contents)
        ])
        
        # Generate extraction
        print(f"   🤖 Extracting fact with {self.model}...")
        if self.enable_mcp_tools:
            print(f"   🔧 MCP tools enabled - LLM can use tools if needed")
        
        messages = self.prompt.format_messages(
            question=question,
            chunks=chunks_text
        )
        
        # Convert to dicts for tool calling
        messages = [{"role": m.type, "content": m.content} for m in messages]
        
        response = self.llm.invoke(messages)
        
        # Check if tool was called
        if self.enable_mcp_tools and hasattr(response, 'tool_calls') and response.tool_calls:
            return self._handle_tool_call(response, messages, chunk_contents, chunk_ids)
        
        # Parse normal response
        content = response.content if isinstance(response.content, str) else str(response.content)
        
        try:
            result: NeedleAnswer = self.parser.parse(content)
        except Exception as e:
            print(f"      ⚠️  Parsing failed: {e}")
            return {
                "answer": None,
                "confidence": 0.0,
                "sources": chunk_ids,
                "retrieved_chunks_content": chunk_contents,
                "reason": f"Failed to parse LLM response: {str(e)}"
            }
        
        return {
            "answer": result.answer,
            "confidence": result.confidence,
            "sources": result.sources,
            "retrieved_chunks_content": chunk_contents,
            "reason": result.reason,
        }
    
    def _handle_tool_call(
        self,
        response,
        messages: List[Dict],
        chunk_contents: List[str],
        chunk_ids: List[str]
    ) -> Dict[str, Any]:
        """Handle MCP tool calls - SIMPLIFIED & FIXED"""
        
        for tool_call in response.tool_calls:
            # Extract tool info (handle both dict and object)
            if isinstance(tool_call, dict):
                tool_name = tool_call['name']
                tool_args = tool_call['args']
                tool_id = tool_call['id']
            else:
                tool_name = tool_call.name
                tool_args = tool_call.args if isinstance(tool_call.args, dict) else tool_call.args.dict()
                tool_id = tool_call.id
            
            if tool_name == 'calculate_days_between':
                print(f"      🔧 Calling MCP tool: {tool_name}")
                
                # Extract dates
                start = tool_args.get('start_date')
                end = tool_args.get('end_date')
                
                if not start or not end:
                    return {
                        "answer": None,
                        "confidence": 0.0,
                        "sources": chunk_ids,
                        "retrieved_chunks_content": chunk_contents,
                        "reason": f"MCP tool missing dates: start={start}, end={end}"
                    }
                
                print(f"         Calculating: {start} to {end}")
                
                try:
                    # Call the MCP tool
                    tool_result = calculate_days_between(start, end)
                    print(f"         Result: {tool_result}")
                    
                    # Extract the number of days - FIXED BUG HERE
                    if isinstance(tool_result, dict):
                        days = tool_result.get('number_of_days', tool_result.get('days', 0))
                    elif isinstance(tool_result, int):
                        days = tool_result
                    else:
                        days = int(str(tool_result))
                    
                    print(f"         ✅ {days} days")
                    
                    # Return result directly (no need to send back to LLM)
                    return {
                        "answer": f"{days} days",
                        "confidence": 0.95,
                        "sources": chunk_ids,
                        "retrieved_chunks_content": chunk_contents,
                        "reason": f"MCP tool calculated date difference: {start} to {end} = {days} days"
                    }
                    
                except Exception as e:
                    print(f"         ❌ MCP tool error: {e}")
                    return {
                        "answer": None,
                        "confidence": 0.0,
                        "sources": chunk_ids,
                        "retrieved_chunks_content": chunk_contents,
                        "reason": f"MCP tool failed: {str(e)}"
                    }
        
        # If we get here, no tool was successfully executed
        return {
            "answer": None,
            "confidence": 0.0,
            "sources": chunk_ids,
            "retrieved_chunks_content": chunk_contents,
            "reason": "Tool call requested but not executed"
        }

