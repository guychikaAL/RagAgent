# Orchestrator - Complete Guide

## 🎯 **What is the Orchestrator?**

The Orchestrator is the **central coordinator** of the RAG pipeline. It orchestrates the multi-agent flow, routing questions to the appropriate agent and managing the entire query lifecycle from start to finish.

```
┌─────────────────────────────────────────────────────────┐
│               ORCHESTRATOR                              │
│        (RAG Pipeline Coordinator)                       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  DOES:                                                  │
│  ✅ Coordinates multi-agent flow                        │
│  ✅ Routes questions to agents                          │
│  ✅ Manages claim filtering                             │
│  ✅ Provides unified response format                    │
│  ✅ Single entry point for RAG system                   │
│                                                         │
│  DOES NOT:                                              │
│  ❌ Retrieve data (Index Layer's job)                   │
│  ❌ Generate answers (Agents' job)                      │
│  ❌ Build retrievers (Index Layer's job)                │
│  ❌ Create embeddings (Index Layer's job)               │
│  ❌ Implement fallback logic (explicit behavior)        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 🎭 **Core Responsibility**

The Orchestrator is a **coordinator, not a worker**. It delegates all work to specialized components:

```
ORCHESTRATOR = CONDUCTOR OF AN ORCHESTRA
─────────────────────────────────────────

Like a conductor:
  • Doesn't play instruments (doesn't retrieve data)
  • Doesn't compose music (doesn't generate answers)
  • Coordinates musicians (routes to agents)
  • Ensures harmony (unified response format)
  • Single leader (single entry point)

Like the Orchestrator:
  • Router Agent: Classifies the question
  • Needle Agent: Answers precise questions
  • Summary Agent: Answers contextual questions
  • Index Layer: Provides retrievers
  • Orchestrator: Coordinates everything
```

---

## 📍 **Where It Fits in the Pipeline**

```
┌─────────────────────────────────────────────────────────┐
│              RAG SYSTEM ARCHITECTURE                    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  BUILD TIME (run once):                                 │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│  1. PDF Ingestion (load PDF)                            │
│     ↓                                                    │
│  2. Claim Segmentation (split into claims)              │
│     ↓                                                    │
│  3. Chunking Layer (create hierarchical nodes)          │
│     ↓                                                    │
│  4. Index Layer (build FAISS index + retrievers)        │
│     ↓                                                    │
│  [Production Index Saved]                               │
│                                                         │
│                                                         │
│  QUERY TIME (run every question):                       │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│  1. Load Production Index                               │
│     ↓                                                    │
│  2. Initialize Agents (Router, Needle, Summary)         │
│     ↓                                                    │
│  3. ORCHESTRATOR ← YOU ARE HERE                         │
│     • Receives user question                            │
│     • Extracts claim filters                            │
│     • Routes to agent                                   │
│     • Returns answer                                    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 🔄 **Complete Orchestration Flow**

### **3-Step Pipeline:**

```
┌──────────────────────────────────────────────────────────┐
│         ORCHESTRATOR PIPELINE (3 STEPS)                  │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  INPUT: User Question                                   │
│         "What is Jon Mor's phone number?"                │
│     ↓                                                     │
│  ┌────────────────────────────────────────────────┐     │
│  │ STEP 0: QUERY PREPROCESSING                    │     │
│  │ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │     │
│  │ • Extract claim number (if mentioned)          │     │
│  │ • Extract claimant name (if mentioned)         │     │
│  │ • Create post-filter retrievers (if needed)    │     │
│  │                                                │     │
│  │ Example:                                       │     │
│  │   "What is Jon Mor's phone?" → claimant="Jon Mor"│   │
│  │   "claim #5 accident date" → claim_number="5"  │     │
│  │                                                │     │
│  │ Result: Filtered retrievers (or default)       │     │
│  └────────────────────────────────────────────────┘     │
│     ↓                                                     │
│  ┌────────────────────────────────────────────────┐     │
│  │ STEP 1: ROUTING                                │     │
│  │ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │     │
│  │ • Call Router Agent                            │     │
│  │ • Classify question: NEEDLE or SUMMARY         │     │
│  │ • Get confidence and reasoning                 │     │
│  │                                                │     │
│  │ Router Decision:                               │     │
│  │   route = "needle"                             │     │
│  │   confidence = 0.95                            │     │
│  │   reason = "Asks for specific phone number"    │     │
│  └────────────────────────────────────────────────┘     │
│     ↓                                                     │
│  ┌────────────────────────────────────────────────┐     │
│  │ STEP 2: EXECUTION                              │     │
│  │ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │     │
│  │ If route == "needle":                          │     │
│  │   → Call Needle Agent                          │     │
│  │   → Use needle_retriever (top_k=3, thresh=0.75)│     │
│  │   → Extract atomic fact                        │     │
│  │                                                │     │
│  │ If route == "summary":                         │     │
│  │   → Call Summary Agent                         │     │
│  │   → Use MapReduce QueryEngine                  │     │
│  │   → Synthesize comprehensive answer            │     │
│  │                                                │     │
│  │ Agent Result:                                  │     │
│  │   answer = "555-1234"                          │     │
│  │   confidence = 1.0                             │     │
│  │   sources = ["chunk_123", "chunk_456"]         │     │
│  │   reason = "Found in contact info section"     │     │
│  └────────────────────────────────────────────────┘     │
│     ↓                                                     │
│  ┌────────────────────────────────────────────────┐     │
│  │ STEP 3: RESPONSE NORMALIZATION                 │     │
│  │ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │     │
│  │ • Combine routing decision + agent result      │     │
│  │ • Create unified response format               │     │
│  │ • Attach metadata                              │     │
│  │                                                │     │
│  │ Unified Response:                              │     │
│  │   {                                            │     │
│  │     "route": "needle",                         │     │
│  │     "answer": "555-1234",                      │     │
│  │     "confidence": 1.0,                         │     │
│  │     "sources": ["chunk_123", "chunk_456"],     │     │
│  │     "reason": "Found in contact info section"  │     │
│  │   }                                            │     │
│  └────────────────────────────────────────────────┘     │
│     ↓                                                     │
│  OUTPUT: Unified Response Dictionary                    │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## 🔍 **Step 0: Query Preprocessing**

### **Purpose:**
Extract claim identifiers from the user's query to enable claim-specific filtering.

### **Why This Matters:**

```
WITHOUT CLAIM FILTERING:
─────────────────────────────────────────
Query: "What is Jon Mor's phone number?"

Retrieval: Semantic search across ALL claims
  • Finds: "Phone: 555-1234" (Jon Mor) ✅
  • Finds: "Phone: 555-5678" (Jane Smith) ❌
  • Finds: "Phone: 555-9012" (Bob Johnson) ❌

Problem: Semantic similarity returns phones from ALL claims!
LLM might pick wrong number!


WITH CLAIM FILTERING:
─────────────────────────────────────────
Query: "What is Jon Mor's phone number?"

Step 1: Extract claimant name → "Jon Mor"
Step 2: Create filtered retriever (claimant_name = "Jon Mor")
Step 3: Retrieval only searches Jon Mor's chunks

Result: Only Jon Mor's phone is retrieved! ✅
```

---

### **Detection Patterns:**

```
┌──────────────────────────────────────────────────────────┐
│           CLAIM IDENTIFIER EXTRACTION                    │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  PATTERN 1: Claim Number                                │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│  Regex: claim\s+number\s+(\d+)                           │
│         claim\s+#(\d+)                                   │
│         form\s+#(\d+)                                    │
│                                                          │
│  Examples:                                              │
│  ✓ "claim number 5" → "5"                                │
│  ✓ "claim #5" → "5"                                      │
│  ✓ "form #20" → "20"                                     │
│  ✓ "AUTO CLAIM FORM #5" → "5"                            │
│                                                          │
│                                                          │
│  PATTERN 2: Claimant Name                               │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│  Regex: \b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b            │
│                                                          │
│  Examples:                                              │
│  ✓ "Jon Mor's phone" → "Jon Mor"                         │
│  ✓ "What is Jane Smith's address?" → "Jane Smith"       │
│  ✓ "Bob Johnson accident date" → "Bob Johnson"          │
│                                                          │
│  Matches: Capitalized first and last names              │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

### **Post-Filter Retriever:**

Since FAISS doesn't support native metadata filtering, the orchestrator creates a **PostFilterRetriever** wrapper:

```
┌──────────────────────────────────────────────────────────┐
│           POST-FILTER RETRIEVER                          │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  HOW IT WORKS:                                          │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│  1. Retrieve top_k * 3 results from FAISS               │
│     WHY: Retrieve MORE to account for filtering         │
│     Example: Want 5 results → retrieve 15               │
│                                                          │
│  2. Filter by metadata (claim_number OR claimant_name)  │
│     WHY: Keep only chunks from target claim             │
│                                                          │
│  3. Return top_k filtered results                       │
│     WHY: Return requested number after filtering        │
│                                                          │
│                                                          │
│  EXAMPLE:                                               │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│  Query: "Jon Mor's phone?"                              │
│  Desired: 5 chunks                                      │
│                                                          │
│  Step 1: Retrieve 15 chunks from FAISS                  │
│    [chunk_1 (Jon Mor), chunk_2 (Jane Smith),            │
│     chunk_3 (Jon Mor), chunk_4 (Bob Johnson),           │
│     chunk_5 (Jon Mor), ...]                             │
│                                                          │
│  Step 2: Filter by claimant_name = "Jon Mor"            │
│    [chunk_1 (Jon Mor), chunk_3 (Jon Mor),               │
│     chunk_5 (Jon Mor), chunk_7 (Jon Mor), ...]          │
│                                                          │
│  Step 3: Return top 5 filtered chunks                   │
│    [chunk_1, chunk_3, chunk_5, chunk_7, chunk_9]        │
│                                                          │
│                                                          │
│  WHY POST-FILTERING?                                    │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│  ✅ FAISS doesn't support native filtering              │
│  ✅ Trade-off: Retrieve more, filter in Python          │
│  ✅ Still fast enough for production                    │
│  ✅ Ensures correct claim isolation                     │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## 🧭 **Step 1: Routing**

### **Purpose:**
Classify the question to determine which agent and retrieval strategy to use.

### **Routing Decision:**

```
┌──────────────────────────────────────────────────────────┐
│              ROUTER AGENT CLASSIFICATION                 │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  INPUT: User Question                                   │
│  OUTPUT: Route Decision                                 │
│                                                          │
│  RouteDecision {                                        │
│    route: "needle" or "summary",                        │
│    confidence: 0.0 to 1.0,                              │
│    reason: "Brief explanation"                          │
│  }                                                       │
│                                                          │
│                                                          │
│  NEEDLE Questions:                                      │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│  • Ask for ONE specific fact                            │
│  • Short, precise answers                               │
│  • Date calculations (MCP tool may be used)             │
│                                                          │
│  Examples:                                              │
│  ✓ "What is Jon Mor's phone number?"                    │
│  ✓ "When did the accident happen?"                      │
│  ✓ "What is the claim amount?"                          │
│  ✓ "How many days between accident and repair?"         │
│                                                          │
│  Retrieval:                                             │
│  → top_k = 3                                            │
│  → similarity_threshold = 0.75                          │
│  → Child chunks only (precise)                          │
│                                                          │
│                                                          │
│  SUMMARY Questions:                                     │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│  • Ask for multiple facts or explanation               │
│  • Require context and synthesis                       │
│  • Longer, comprehensive answers                       │
│                                                          │
│  Examples:                                              │
│  ✓ "Summarize Jon Mor's claim"                          │
│  ✓ "What happened in the accident?"                     │
│  ✓ "What are the main details?"                         │
│  ✓ "Explain the claim status"                           │
│                                                          │
│  Retrieval:                                             │
│  → Uses MapReduce QueryEngine                           │
│  → Retrieves many chunks                                │
│  → Hierarchical summarization (map → reduce)            │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

### **Routing Flow:**

```
User Question
     ↓
┌──────────────────────────────────┐
│   Router Agent                   │
│   ━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│   • Analyze question intent      │
│   │ • Classify: needle/summary   │
│   • Return confidence + reason   │
└──────────────────────────────────┘
     ↓
Route Decision:
  {
    "route": "needle",
    "confidence": 0.95,
    "reason": "Asks for specific phone number"
  }
     ↓
[Orchestrator proceeds to execution]
```

---

## ⚡ **Step 2: Execution**

### **Purpose:**
Call the appropriate agent with the appropriate retriever/query engine.

### **Needle Path:**

```
┌──────────────────────────────────────────────────────────┐
│               NEEDLE EXECUTION PATH                      │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Trigger: route == "needle"                             │
│                                                          │
│  1. Call Needle Agent                                   │
│     ↓                                                     │
│  2. Needle Agent retrieves chunks                       │
│     • Uses needle_retriever (filtered if claim detected)│
│     • top_k = 3                                         │
│     • similarity_threshold = 0.75                       │
│     • Child chunks only (precise)                       │
│     ↓                                                     │
│  3. Needle Agent extracts fact                          │
│     • LLM prompt: "Extract the answer"                  │
│     • Structured output (Pydantic)                      │
│     • May call MCP tool for date calculations           │
│     ↓                                                     │
│  4. Return result                                       │
│     {                                                    │
│       "answer": "555-1234",                             │
│       "confidence": 1.0,                                │
│       "sources": ["chunk_123", "chunk_456"],            │
│       "reason": "Found in contact info section"         │
│     }                                                    │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

### **Summary Path:**

```
┌──────────────────────────────────────────────────────────┐
│              SUMMARY EXECUTION PATH                      │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Trigger: route == "summary"                            │
│                                                          │
│  PREFERRED: MapReduce QueryEngine                       │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│  1. Call Summary Agent with MapReduce                   │
│     ↓                                                     │
│  2. MapReduce retrieves many chunks                     │
│     • No similarity threshold (high recall)             │
│     • Both parent and child chunks                      │
│     ↓                                                     │
│  3. MapReduce performs hierarchical summarization       │
│     • Map: Summarize each chunk                         │
│     • Reduce: Combine summaries into final answer       │
│     ↓                                                     │
│  4. Return comprehensive answer                         │
│     {                                                    │
│       "answer": "Jon Mor's claim involves...",          │
│       "confidence": 0.9,                                │
│       "sources": ["chunk_1", "chunk_2", ...],           │
│       "reason": "Synthesized from incident section"     │
│     }                                                    │
│                                                          │
│                                                          │
│  FALLBACK: Simple Retriever                             │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│  If MapReduce not available:                            │
│  1. Use summary_retriever                               │
│  2. Retrieve top_k=8 chunks                             │
│  3. Synthesize answer from chunks                       │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## 📊 **Step 3: Response Normalization**

### **Purpose:**
Create a unified response format that combines routing metadata with agent results.

### **Unified Response Format:**

```
┌──────────────────────────────────────────────────────────┐
│              UNIFIED RESPONSE STRUCTURE                  │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  {                                                       │
│    "route": str,              # "needle" or "summary"   │
│    "answer": str,              # Final answer           │
│    "confidence": float,        # 0.0 to 1.0             │
│    "sources": List[str],       # Chunk IDs used         │
│    "retrieved_chunks_content": List[str],  # Actual text│
│    "reason": str               # Agent's reasoning      │
│  }                                                       │
│                                                          │
│                                                          │
│  WHY THIS FORMAT?                                       │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│  ✅ Consistent across all questions                     │
│  ✅ Contains all metadata for debugging                 │
│  ✅ Easy to parse for external systems                  │
│  ✅ Includes traceability (sources, reason)             │
│  ✅ Standard interface for evaluation                   │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

### **Example Responses:**

```
NEEDLE RESPONSE:
─────────────────────────────────────────
{
  "route": "needle",
  "answer": "555-1234",
  "confidence": 1.0,
  "sources": ["chunk_abc123", "chunk_def456"],
  "retrieved_chunks_content": [
    "Phone: 555-1234",
    "Contact: Jon Mor, 555-1234"
  ],
  "reason": "Found exact phone number in contact section"
}


SUMMARY RESPONSE:
─────────────────────────────────────────
{
  "route": "summary",
  "answer": "Jon Mor's claim involves a vehicle accident that occurred on 2024-01-24. The incident took place at Main St. The claim amount is $5,000 and the status is approved.",
  "confidence": 0.9,
  "sources": ["chunk_1", "chunk_2", "chunk_3", "chunk_4"],
  "retrieved_chunks_content": [
    "Incident Date: 2024-01-24",
    "Location: Main St",
    "Claim Amount: $5,000",
    "Status: Approved"
  ],
  "reason": "Synthesized comprehensive summary from incident and status sections"
}


MCP TOOL USAGE (Date Calculation):
─────────────────────────────────────────
{
  "route": "needle",
  "answer": "25 days",
  "confidence": 1.0,
  "sources": ["chunk_xyz789", "chunk_abc123"],
  "retrieved_chunks_content": [
    "Incident Date: 2024-01-24",
    "Repair Appointment: 2024-02-18"
  ],
  "reason": "Used MCP date_calculator tool: calculate_days_between(2024-01-24, 2024-02-18) = 25 days"
}
```

---

## 🎓 **Key Concepts**

### **1. Dependency Injection**

```
WHY DEPENDENCY INJECTION?
─────────────────────────────────────────

WHAT IT MEANS:
  All components (agents, retrievers) are created
  OUTSIDE the orchestrator and passed in.

WHY:
  ✅ Orchestrator has ZERO creation logic
  ✅ Each component can be configured independently
  ✅ Easy to swap implementations
  ✅ Easy to test with mocks
  ✅ No hidden dependencies


EXAMPLE:
─────────────────────────────────────────
# BAD: Orchestrator creates components
class Orchestrator:
    def __init__(self):
        self.router = RouterAgent()  # Hardcoded!
        self.needle = NeedleAgent()  # Hardcoded!
        # Can't test, can't swap!


# GOOD: Components injected
class Orchestrator:
    def __init__(self, router_agent, needle_agent, ...):
        self.router_agent = router_agent  # Injected!
        self.needle_agent = needle_agent  # Injected!
        # Easy to test, easy to swap!
```

---

### **2. Stateless Design**

```
STATELESS = NO MEMORY BETWEEN CALLS
─────────────────────────────────────────

WHAT IT MEANS:
  Each call to orchestrator.run() is independent.
  No state is stored between questions.

WHY:
  ✅ Thread-safe (multiple questions in parallel)
  ✅ No memory leaks
  ✅ Predictable behavior
  ✅ Easy to scale (no session management)


EXAMPLE:
─────────────────────────────────────────
# First question
response1 = orchestrator.run("What is Jon Mor's phone?")

# Second question (completely independent)
response2 = orchestrator.run("What is Jane Smith's address?")

# NO state is shared between these calls!
```

---

### **3. Separation of Concerns**

```
EACH COMPONENT HAS ONE JOB:
─────────────────────────────────────────

┌──────────────────────────────────┐
│ Router Agent                     │
│ Job: Classify questions          │
│ Does NOT: Retrieve or answer     │
└──────────────────────────────────┘

┌──────────────────────────────────┐
│ Needle Agent                     │
│ Job: Extract atomic facts        │
│ Does NOT: Route or build index   │
└──────────────────────────────────┘

┌──────────────────────────────────┐
│ Summary Agent                    │
│ Job: Synthesize comprehensive    │
│ Does NOT: Route or build index   │
└──────────────────────────────────┘

┌──────────────────────────────────┐
│ Index Layer                      │
│ Job: Build retrievers            │
│ Does NOT: Answer questions       │
└──────────────────────────────────┘

┌──────────────────────────────────┐
│ Orchestrator                     │
│ Job: Coordinate components       │
│ Does NOT: Retrieve, answer, route│
└──────────────────────────────────┘
```

---

### **4. Explicit Behavior (No Fallbacks)**

```
WHY NO FALLBACK LOGIC?
─────────────────────────────────────────

FALLBACK = Silent failure masking
EXPLICIT = Errors surface immediately

EXAMPLE:
─────────────────────────────────────────
# BAD: Silent fallback
if route == "needle":
    try:
        return needle_agent.answer(...)
    except:
        return "I don't know"  # User never knows what failed!


# GOOD: Explicit behavior
if route == "needle":
    return needle_agent.answer(...)  # Errors surface!
elif route == "summary":
    return summary_agent.answer(...)
else:
    raise ValueError(f"Invalid route: {route}")  # Explicit error!


WHY:
  ✅ Errors are caught in development
  ✅ No silent failures in production
  ✅ Easier debugging
  ✅ Users get meaningful errors
```

---

## 🔗 **Integration Example**

### **Complete Usage:**

```python
from RAG.Orchestration import Orchestrator
from RAG.Agents import create_router_agent, create_needle_agent, create_summary_agent
from RAG.Index_Layer import IndexLayer

# Step 1: Load index
index_layer = IndexLayer()
index_layer.load_index("production_index")

# Step 2: Create agents
router_agent = create_router_agent(model="gpt-4o-mini", temperature=0.0)
needle_agent = create_needle_agent(model="gpt-4o-mini", temperature=0.0, enable_mcp_tools=True)
summary_agent = create_summary_agent(model="gpt-4o-mini", temperature=0.0, enable_mcp_tools=True)

# Step 3: Get retrievers from index layer
needle_retriever = index_layer.get_needle_retriever(top_k=3, similarity_threshold=0.75)
map_reduce_engine = index_layer.get_map_reduce_query_engine()

# Step 4: Create orchestrator (dependency injection!)
orchestrator = Orchestrator(
    router_agent=router_agent,
    needle_agent=needle_agent,
    summary_agent=summary_agent,
    needle_retriever=needle_retriever,
    map_reduce_query_engine=map_reduce_engine
)

# Step 5: Ask questions
response = orchestrator.run("What is Jon Mor's phone number?")

print(f"Route: {response['route']}")
print(f"Answer: {response['answer']}")
print(f"Confidence: {response['confidence']}")
print(f"Sources: {response['sources']}")
print(f"Reason: {response['reason']}")
```

---

### **Output:**

```
======================================================================
🚀 RAG PIPELINE STARTED
======================================================================
Question: What is Jon Mor's phone number?

🔍 Detected claimant name: Jon Mor
   Creating post-filtered retrievers...
   ✅ Will filter to claimant_name = Jon Mor

[STEP 1] ROUTING
──────────────────────────────────────────────────────────────────────
✓ Route:      NEEDLE
✓ Confidence: 0.95
✓ Reason:     Question asks for specific phone number

[STEP 2] EXECUTION
──────────────────────────────────────────────────────────────────────
→ Executing NEEDLE AGENT...
   Retrieved 3 chunks (all from Jon Mor's claim)
   Extracted answer: 555-1234

[STEP 3] RESPONSE
──────────────────────────────────────────────────────────────────────
✓ Route:      NEEDLE
✓ Answer:     555-1234
✓ Confidence: 1.0
✓ Sources:    2 chunk(s)
✓ Reason:     Found exact phone number in contact section

======================================================================
✅ RAG PIPELINE COMPLETED
======================================================================
```

---

## 📊 **Orchestrator vs. Other Components**

```
┌─────────────────────────────────────────────────────────┐
│         COMPONENT COMPARISON                            │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ORCHESTRATOR:                                          │
│  • Coordinates multi-agent flow                         │
│  • Manages claim filtering                              │
│  • Provides unified response                            │
│  • Single entry point                                   │
│  • NO retrieval, NO answering, NO routing logic         │
│                                                         │
│  ROUTER AGENT:                                          │
│  • Classifies questions (needle vs. summary)            │
│  • Returns route decision                               │
│  • NO retrieval, NO answering                           │
│                                                         │
│  NEEDLE AGENT:                                          │
│  • Extracts atomic facts                                │
│  • Uses needle retriever                                │
│  • May call MCP tools                                   │
│  • NO routing, NO building index                        │
│                                                         │
│  SUMMARY AGENT:                                         │
│  • Synthesizes comprehensive answers                    │
│  • Uses MapReduce or summary retriever                  │
│  • NO routing, NO building index                        │
│                                                         │
│  INDEX LAYER:                                           │
│  • Builds FAISS index                                   │
│  • Creates retrievers                                   │
│  • Manages embeddings                                   │
│  • NO answering, NO routing                             │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## ✅ **Summary: Orchestrator**

```
┌─────────────────────────────────────────────────────────┐
│               ORCHESTRATOR SUMMARY                      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ROLE:                                                  │
│  Central coordinator of the RAG pipeline                │
│                                                         │
│  RESPONSIBILITY:                                        │
│  • Coordinate multi-agent flow                          │
│  • Manage claim filtering                               │
│  • Provide unified response format                      │
│                                                         │
│  DOES NOT DO:                                           │
│  ❌ Retrieve data (Index Layer's job)                   │
│  ❌ Generate answers (Agents' job)                      │
│  ❌ Classify questions (Router Agent's job)             │
│  ❌ Build retrievers (Index Layer's job)                │
│                                                         │
│  3-STEP PIPELINE:                                       │
│  0. Query Preprocessing (extract claim filters)         │
│  1. Routing (call Router Agent)                         │
│  2. Execution (call Needle/Summary Agent)               │
│  3. Response Normalization (unified format)             │
│                                                         │
│  KEY PRINCIPLES:                                        │
│  ✅ Dependency injection (no hardcoded components)      │
│  ✅ Stateless design (no memory between calls)          │
│  ✅ Separation of concerns (one job only)               │
│  ✅ Explicit behavior (no silent fallbacks)             │
│                                                         │
│  CLAIM FILTERING:                                       │
│  • Detects claim numbers ("claim #5")                   │
│  • Detects claimant names ("Jon Mor's phone")           │
│  • Creates PostFilterRetriever for claim isolation      │
│  • Prevents cross-claim contamination                   │
│                                                         │
│  UNIFIED RESPONSE:                                      │
│  {                                                      │
│    "route": "needle" | "summary",                       │
│    "answer": str,                                       │
│    "confidence": float,                                 │
│    "sources": List[str],                                │
│    "reason": str                                        │
│  }                                                      │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 📁 **Files**

| File | Purpose |
|------|---------|
| `orchestrator.py` | Main orchestrator implementation |
| `__init__.py` | Module exports |
| `orchestrator-explained.md` | This documentation |

---

## 🎯 **Key Takeaways**

```
1. COORDINATOR, NOT WORKER:
   Orchestrator delegates all work to specialized components.

2. DEPENDENCY INJECTION:
   All components (agents, retrievers) are injected, not created.

3. 3-STEP PIPELINE:
   Preprocessing → Routing → Execution → Normalization

4. CLAIM FILTERING:
   Automatically detects claim identifiers and filters retrieval.

5. STATELESS:
   No memory between calls (thread-safe, scalable).

6. UNIFIED RESPONSE:
   Consistent format for all questions (easy integration).

7. EXPLICIT BEHAVIOR:
   No silent fallbacks (errors surface immediately).

8. SINGLE ENTRY POINT:
   One method (orchestrator.run()) for the entire RAG pipeline.
```

---

**Built for RagAgentv2 - Auto Claims RAG System** 🎯🚀

🎯 What's Included:

RAG/Orchestration/orchestrator-explained.md
├─ 🎯 What is the Orchestrator?
├─ 🎭 Core Responsibility (Coordinator, not worker)
│
├─ 📍 Where It Fits in the Pipeline
│   ├─ Build time (index creation)
│   └─ Query time (orchestration)
│
├─ 🔄 Complete Orchestration Flow (3 Steps)
│   ├─ Overview diagram
│   │
│   ├─ Step 0: Query Preprocessing
│   │   ├─ Purpose and importance
│   │   ├─ Detection patterns (claim number & claimant name)
│   │   ├─ PostFilterRetriever explained
│   │   └─ Examples (with and without filtering)
│   │
│   ├─ Step 1: Routing
│   │   ├─ Router Agent classification
│   │   ├─ Needle vs. Summary questions
│   │   ├─ Routing flow diagram
│   │   └─ Examples for each route
│   │
│   ├─ Step 2: Execution
│   │   ├─ Needle Path (atomic fact extraction)
│   │   ├─ Summary Path (MapReduce or simple retriever)
│   │   └─ Complete flow for each path
│   │
│   └─ Step 3: Response Normalization
│       ├─ Unified response format
│       └─ Example responses (Needle, Summary, MCP)
│
├─ 🎓 Key Concepts
│   ├─ 1. Dependency Injection (why & how)
│   ├─ 2. Stateless Design (no memory)
│   ├─ 3. Separation of Concerns (one job only)
│   └─ 4. Explicit Behavior (no silent fallbacks)
│
├─ 🔗 Integration Example
│   ├─ Complete code walkthrough
│   └─ Sample output with logs
│
├─ 📊 Orchestrator vs. Other Components
│   └─ Comparison table
│
├─ ✅ Summary
├─ 📁 Files Reference
└─ 🎯 Key Takeaways



🎯 Key Takeaways:

1. COORDINATOR, NOT WORKER:
   Orchestrator delegates ALL work to specialized components
   (Doesn't retrieve, doesn't answer, doesn't route)

2. 3-STEP PIPELINE:
   Step 0: Extract claim filters (claimant name, claim number)
   Step 1: Route question (Router Agent)
   Step 2: Execute with agent (Needle or Summary)
   Step 3: Return unified response

3. CLAIM FILTERING:
   "Jon Mor's phone?" → filters to Jon Mor's chunks only
   "claim #5 amount" → filters to claim #5 only
   PostFilterRetriever: Retrieve 3x, filter by metadata

4. DEPENDENCY INJECTION:
   All agents and retrievers are created externally
   Orchestrator has ZERO creation logic
   Easy to test, easy to swap

5. STATELESS:
   No memory between questions
   Thread-safe and scalable

6. UNIFIED RESPONSE:
   {
     "route": "needle" | "summary",
     "answer": str,
     "confidence": float,
     "sources": List[str],
     "reason": str
   }

7. EXPLICIT BEHAVIOR:
   No silent fallbacks
   Errors surface immediately
   Easier debugging

8. SINGLE ENTRY POINT:
   orchestrator.run(question) → complete RAG pipeline