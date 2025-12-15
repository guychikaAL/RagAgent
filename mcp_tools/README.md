# MCP-Style Tools

This directory contains minimal MCP-style tools that demonstrate how to extend LLM capabilities beyond text generation through **deterministic external computation**.

## Overview

**MCP (Model Context Protocol) Pattern:**
```
Natural Language Query
        ↓
    LLM Agent
    ├─ Understands intent
    ├─ Extracts structured data
    └─ Calls appropriate tool
            ↓
    External Tool
    ├─ Performs computation
    └─ Returns exact result
            ↓
    LLM formats response
```

## Why MCP Tools?

### ❌ What LLMs Are Bad At:
- Precise arithmetic
- Date/time calculations
- Complex numerical operations
- Deterministic computation
- Edge case handling

### ✅ What LLMs Are Good At:
- Natural language understanding
- Intent recognition
- Information extraction
- Tool orchestration
- Response formatting

### 🎯 The Solution: MCP Tools
Combine LLM strengths with external computation for:
- **Exact results** (no approximation)
- **Reliable computation** (no hallucination)
- **Proper error handling** (no silent failures)
- **Extended capabilities** (without retraining)

## Available Tools

### 1. Date Calculator (`date_calculator.py`)

**Purpose:** Calculate exact number of days between two dates

**Why it exists:**
- LLMs cannot reliably handle date arithmetic
- Leap years, month boundaries, timezone issues
- Edge cases require deterministic computation

**Interface:**
```python
from mcp_tools import calculate_days_between

result = calculate_days_between(
    start_date="2024-01-01",
    end_date="2024-12-31"
)

# Returns:
# {
#     'success': True,
#     'number_of_days': 365,
#     'start_date': '2024-01-01',
#     'end_date': '2024-12-31'
# }
```

**Test:** Run `test_date_difference_mcp.ipynb` to see:
- Natural language query handling
- Tool invocation
- Error handling
- Complex real-world examples

## Testing

### Run Date Calculator Tests:
```bash
# From project root
jupyter notebook mcp_tools/test_date_difference_mcp.ipynb

# Or run standalone tests:
cd mcp_tools
python date_calculator.py
```

### Expected Output:
```
Testing Date Calculator Tool
============================================================

1. Normal case (Jan 1 to Jan 10, 2024):
   Result: {'success': True, 'number_of_days': 9, ...}

2. Reverse order (Jan 10 to Jan 1, 2024):
   Result: {'success': True, 'number_of_days': -9, ...}

3. Leap year (Feb 28 to Mar 1, 2024):
   Result: {'success': True, 'number_of_days': 2, ...}

...

✅ Tool tests complete
```

## Key Principles

### 1. Deterministic Computation
```python
# ❌ LLM: "approximately 104 days"
# ✅ Tool: 104 (exact integer)
```

### 2. No Hallucination
```python
# ❌ LLM might forget leap years
# ✅ Tool uses datetime library (guaranteed correct)
```

### 3. Proper Error Handling
```python
# ❌ LLM might ignore invalid dates
# ✅ Tool validates and returns clear error messages
```

### 4. Clear Separation of Concerns
```
LLM:  Natural language ←→ Structured data
Tool: Structured data  ←→ Exact computation
```

## Integration with LLM Agents

### Example: OpenAI Function Calling

```python
from openai import OpenAI
from mcp_tools import calculate_days_between

client = OpenAI()

tools = [
    {
        "type": "function",
        "function": {
            "name": "calculate_days_between",
            "description": "Calculate exact days between two dates",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date (YYYY-MM-DD)"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date (YYYY-MM-DD)"
                    }
                },
                "required": ["start_date", "end_date"]
            }
        }
    }
]

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "user", "content": "How many days until Christmas from today?"}
    ],
    tools=tools,
    tool_choice="auto"
)

# LLM decides to call the tool
if response.choices[0].message.tool_calls:
    tool_call = response.choices[0].message.tool_calls[0]
    args = json.loads(tool_call.function.arguments)
    
    # Execute the tool
    result = calculate_days_between(
        start_date=args['start_date'],
        end_date=args['end_date']
    )
    
    # Send result back to LLM for final response
    # ...
```

### Example: LangChain Integration

```python
from langchain.tools import Tool
from mcp_tools import calculate_days_between

def date_diff_wrapper(input_str: str) -> str:
    """Wrapper for LangChain"""
    # Parse input: "2024-01-01,2024-12-31"
    start, end = input_str.split(',')
    result = calculate_days_between(start.strip(), end.strip())
    return str(result['number_of_days']) if result['success'] else result['error']

date_tool = Tool(
    name="calculate_days_between",
    func=date_diff_wrapper,
    description="Calculate exact days between dates (format: YYYY-MM-DD,YYYY-MM-DD)"
)

# Use with agent
from langchain.agents import initialize_agent, AgentType

agent = initialize_agent(
    tools=[date_tool],
    llm=your_llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION
)

response = agent.run("How many days from Jan 1 to Dec 31, 2024?")
```

## Real-World Use Cases

### 1. Project Management
```
User: "My sprint is 2 weeks, started Dec 1. When does it end?"
LLM:  Extracts start date, calculates end date
Tool: Provides exact day count
LLM:  "Your sprint ends on December 15 (14 days from start)"
```

### 2. Deadline Calculations
```
User: "Paper due March 15, today is Feb 20. How much time left?"
LLM:  Extracts both dates
Tool: calculate_days_between('2024-02-20', '2024-03-15')
LLM:  "You have 24 days remaining"
```

### 3. Historical Analysis
```
User: "How long was the Apollo 11 mission? (July 16-24, 1969)"
LLM:  Recognizes date calculation needed
Tool: Returns exact duration
LLM:  "The Apollo 11 mission lasted 8 days"
```

## Best Practices

### ✅ DO:
- Use tools for **deterministic computation**
- Let LLM handle **natural language** understanding
- Validate inputs in the tool
- Return structured, parseable outputs
- Include clear error messages

### ❌ DON'T:
- Let LLM attempt arithmetic it's bad at
- Guess or approximate when exact values are needed
- Skip input validation
- Return ambiguous results
- Use tools for tasks LLMs can handle well

## Future Tools

Potential additions to this directory:
- **Currency converter** (exact exchange rates)
- **Unit converter** (precise conversions)
- **File size calculator** (exact byte counts)
- **Checksum validator** (hash verification)
- **Data validator** (schema checking)

## Testing Strategy

Each tool includes:
1. **Inline tests** (run the .py file directly)
2. **Interactive notebook** (test_*.ipynb)
3. **Integration examples** (in notebook)
4. **Error case coverage** (invalid inputs)

## Resources

- [Model Context Protocol Spec](https://modelcontextprotocol.io/)
- [OpenAI Function Calling](https://platform.openai.com/docs/guides/function-calling)
- [LangChain Tools](https://python.langchain.com/docs/modules/agents/tools/)
- [LlamaIndex Tools](https://docs.llamaindex.ai/en/stable/module_guides/deploying/agents/tools/)

---

**Remember:** MCP tools extend LLM capabilities without changing the model. They demonstrate the principle:

> **Specialized computation + General intelligence = Powerful AI systems**
