# RAG System Architecture & Flow Documentation
**RAG Agent v2 - Complete Query Processing Pipeline**

---

## 📋 Table of Contents
1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Complete Query Flow](#complete-query-flow)
4. [Layer-by-Layer Breakdown](#layer-by-layer-breakdown)
5. [Key Parameters Explained](#key-parameters-explained)
6. [Example Walkthrough](#example-walkthrough)
7. [Performance Metrics](#performance-metrics)

---

## 🎯 Overview

This RAG (Retrieval-Augmented Generation) system processes user queries through multiple specialized layers:
- **Orchestrator**: Coordinates the entire pipeline
- **Router Agent**: Classifies query type (NEEDLE vs SUMMARY)
- **Needle/Summary Agents**: Handle specific query types
- **Index Layer**: Performs vector search and retrieval
- **LLM**: Generates final answers

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INTERFACE                            │
│                   (Query Input / Answer Output)                  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
        ╔════════════════════════════════════════╗
        ║         ORCHESTRATOR LAYER             ║
        ║   (RAG/Orchestration/orchestrator.py)  ║
        ║                                        ║
        ║  • Entry point for all queries         ║
        ║  • Coordinates agent workflow          ║
        ║  • Formats final response              ║
        ╚════════════════╦═══════════════════════╝
                         │
         ┌───────────────┴───────────────┐
         │                               │
         ▼                               ▼
┌─────────────────┐            ┌─────────────────┐
│  ROUTER AGENT   │            │  AGENTS LAYER   │
│                 │            │                 │
│  • Query        │───────────▶│  • Needle Agent │
│    Classification│            │  • Summary Agent│
│  • Route         │            │                 │
│    Decision      │            │  Request        │
│                 │            │  Retrieval      │
└─────────────────┘            └────────┬────────┘
                                        │
                                        ▼
                        ╔═══════════════════════════════╗
                        ║      INDEX LAYER ⭐          ║
                        ║  (Retrieval Engine)          ║
                        ║                              ║
                        ║  1. Embed Query              ║
                        ║  2. Vector Search            ║
                        ║  3. Apply Filters            ║
                        ║  4. Return Chunks            ║
                        ╚═══════════════════════════════╝
                                        │
                                        ▼
                        ┌───────────────────────────────┐
                        │   VECTOR DATABASE             │
                        │   • All document chunks       │
                        │   • Pre-computed embeddings   │
                        │   • Metadata & filters        │
                        └───────────────────────────────┘
```

---

## 🔄 Complete Query Flow

### Visual Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        USER QUERY                            │
│              "What is Jon Mor's phone number?"               │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │   STEP 1: ORCHESTRATOR (Entry)        │
        │   RAG/Orchestration/orchestrator.py   │
        │                                        │
        │   • Receives user query                │
        │   • Initializes processing             │
        │   • Sends to Router Agent              │
        └───────────────┬───────────────────────┘
                        │
                        ▼
        ┌───────────────────────────────────────┐
        │   STEP 2: ROUTER AGENT (Classify)     │
        │   RAG/Agents/router_agent.py          │
        │  ┌─────────────────────────────────┐  │
        │  │ 🤖 LLM: gpt-4o-mini            │  │
        │  │ Analyzes: Query type?           │  │
        │  │ Decision: "NEEDLE"              │  │
        │  │ Reason: Specific fact needed    │  │
        │  │ Confidence: 1.0                 │  │
        │  └─────────────────────────────────┘  │
        └───────────────┬───────────────────────┘
                        │
                        ▼
        ┌───────────────────────────────────────┐
        │   STEP 3: NEEDLE AGENT (Handle)       │
        │   RAG/Agents/needle_agent.py          │
        │                                        │
        │   • Receives NEEDLE route              │
        │   • Prepares retrieval request         │
        │   • Calls needle_retriever             │
        └───────────────┬───────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────────────────┐
│          STEP 4: INDEX LAYER (Retrieval) ⭐                    │
│          RAG/Index_Layer/index_layer.py                        │
│                                                                 │
│  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓   │
│  ┃ STEP 4A: EMBED QUERY                                  ┃   │
│  ┃ ┌────────────────────────────────────────────────┐   ┃   │
│  ┃ │ Embedding Model: text-embedding-3-small       │   ┃   │
│  ┃ │                                                │   ┃   │
│  ┃ │ Input (Text):                                 │   ┃   │
│  ┃ │   "What is Jon Mor's phone number?"           │   ┃   │
│  ┃ │                                                │   ┃   │
│  ┃ │ Output (Vector - 1536 dimensions):            │   ┃   │
│  ┃ │   [0.234, -0.456, 0.678, 0.123, -0.891, ...] │   ┃   │
│  ┃ └────────────────────────────────────────────────┘   ┃   │
│  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛   │
│                              │                                  │
│                              ▼                                  │
│  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓   │
│  ┃ STEP 4B: VECTOR SEARCH (Calculate Similarities)      ┃   │
│  ┃ ┌────────────────────────────────────────────────┐   ┃   │
│  ┃ │ Compare query vector with ALL chunks in DB     │   ┃   │
│  ┃ │                                                │   ┃   │
│  ┃ │ Cosine Similarity Calculation:                │   ┃   │
│  ┃ │                                                │   ┃   │
│  ┃ │ Query: [0.234, -0.456, 0.678, ...]            │   ┃   │
│  ┃ │                                                │   ┃   │
│  ┃ │ Chunk 1 [0.231, -0.451, 0.682, ...] → 0.95 ✅│   ┃   │
│  ┃ │   "Jon Mor, Phone: (555) 100-2000"            │   ┃   │
│  ┃ │                                                │   ┃   │
│  ┃ │ Chunk 2 [0.198, -0.423, 0.701, ...] → 0.82 ✅│   ┃   │
│  ┃ │   "Contact Info: Jon Mor..."                  │   ┃   │
│  ┃ │                                                │   ┃   │
│  ┃ │ Chunk 3 [0.241, -0.389, 0.655, ...] → 0.78 ✅│   ┃   │
│  ┃ │   "Claimant: Jon Mor, Account..."             │   ┃   │
│  ┃ │                                                │   ┃   │
│  ┃ │ Chunk 4 [0.112, -0.298, 0.544, ...] → 0.68   │   ┃   │
│  ┃ │   "Jon Mor vehicle: Toyota..."                │   ┃   │
│  ┃ │                                                │   ┃   │
│  ┃ │ Chunk 5 [0.034, 0.123, -0.234, ...] → 0.45   │   ┃   │
│  ┃ │   "Eli Cohen claim details..."                │   ┃   │
│  ┃ │                                                │   ┃   │
│  ┃ │ ... (all other chunks ranked)                 │   ┃   │
│  ┃ └────────────────────────────────────────────────┘   ┃   │
│  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛   │
│                              │                                  │
│                              ▼                                  │
│  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓   │
│  ┃ STEP 4C: APPLY FILTERS ⚙️                            ┃   │
│  ┃ ┌────────────────────────────────────────────────┐   ┃   │
│  ┃ │ ⚙️ Settings:                                  │   ┃   │
│  ┃ │   • similarity_threshold = 0.75               │   ┃   │
│  ┃ │   • top_k = 3                                 │   ┃   │
│  ┃ │                                                │   ┃   │
│  ┃ │ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │   ┃   │
│  ┃ │                                                │   ┃   │
│  ┃ │ 🔍 Filter Step 1: similarity_threshold        │   ┃   │
│  ┃ │    (Keep only chunks with score ≥ 0.75)      │   ┃   │
│  ┃ │                                                │   ┃   │
│  ┃ │    ├─ Chunk 1: 0.95 ≥ 0.75 ✅ KEEP           │   ┃   │
│  ┃ │    ├─ Chunk 2: 0.82 ≥ 0.75 ✅ KEEP           │   ┃   │
│  ┃ │    ├─ Chunk 3: 0.78 ≥ 0.75 ✅ KEEP           │   ┃   │
│  ┃ │    ├─ Chunk 4: 0.68 < 0.75 ❌ FILTERED OUT   │   ┃   │
│  ┃ │    └─ Chunk 5: 0.45 < 0.75 ❌ FILTERED OUT   │   ┃   │
│  ┃ │                                                │   ┃   │
│  ┃ │    Remaining: 3 chunks pass threshold         │   ┃   │
│  ┃ │                                                │   ┃   │
│  ┃ │ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │   ┃   │
│  ┃ │                                                │   ┃   │
│  ┃ │ 🔝 Filter Step 2: top_k                       │   ┃   │
│  ┃ │    (Take top 3 highest-scoring chunks)        │   ┃   │
│  ┃ │                                                │   ┃   │
│  ┃ │    Result: 3 chunks (all 3 qualify)           │   ┃   │
│  ┃ └────────────────────────────────────────────────┘   ┃   │
│  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛   │
│                              │                                  │
│                              ▼                                  │
│  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓   │
│  ┃ STEP 4D: RETURN CHUNK TEXTS                           ┃   │
│  ┃ ┌────────────────────────────────────────────────┐   ┃   │
│  ┃ │ 📦 Final Retrieved Chunks:                    │   ┃   │
│  ┃ │                                                │   ┃   │
│  ┃ │ 1️⃣ Chunk 1 (score: 0.95):                    │   ┃   │
│  ┃ │    "Jon Mor, Phone: (555) 100-2000,           │   ┃   │
│  ┃ │     Email: jon.mor@email.com..."              │   ┃   │
│  ┃ │                                                │   ┃   │
│  ┃ │ 2️⃣ Chunk 2 (score: 0.82):                    │   ┃   │
│  ┃ │    "Contact Information for Jon Mor:          │   ┃   │
│  ┃ │     Primary phone, secondary contact..."      │   ┃   │
│  ┃ │                                                │   ┃   │
│  ┃ │ 3️⃣ Chunk 3 (score: 0.78):                    │   ┃   │
│  ┃ │    "Claimant: Jon Mor, Account: ACC9900460,   │   ┃   │
│  ┃ │     Contact details on file..."               │   ┃   │
│  ┃ └────────────────────────────────────────────────┘   ┃   │
│  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛   │
└─────────────────────────┬──────────────────────────────────────┘
                          │
                          ▼
        ┌───────────────────────────────────────┐
        │   STEP 5: NEEDLE AGENT (Extract)      │
        │   RAG/Agents/needle_agent.py          │
        │  ┌─────────────────────────────────┐  │
        │  │ 🤖 LLM: gpt-4o-mini            │  │
        │  │                                 │  │
        │  │ Prompt:                         │  │
        │  │ "Given these chunks, extract    │  │
        │  │  Jon Mor's phone number.        │  │
        │  │                                 │  │
        │  │  If not found, return None."    │  │
        │  │                                 │  │
        │  │ LLM reads 3 chunks...           │  │
        │  │ LLM finds phone in Chunk 1      │  │
        │  │ LLM extracts: "(555) 100-2000"  │  │
        │  └─────────────────────────────────┘  │
        └───────────────┬───────────────────────┘
                        │
                        ▼
        ┌───────────────────────────────────────┐
        │   STEP 6: ORCHESTRATOR (Format)       │
        │   RAG/Orchestration/orchestrator.py   │
        │  ┌─────────────────────────────────┐  │
        │  │ Format response:                │  │
        │  │ {                               │  │
        │  │   "answer": "(555) 100-2000",   │  │
        │  │   "route": "NEEDLE",            │  │
        │  │   "confidence": 0.95,           │  │
        │  │   "sources": ["chunk_1"],       │  │
        │  │   "retrieved_chunks": [...]     │  │
        │  │ }                               │  │
        │  └─────────────────────────────────┘  │
        └───────────────┬───────────────────────┘
                        │
                        ▼
            ┌───────────────────────┐
            │    FINAL ANSWER       │
            │                       │
            │  "(555) 100-2000"     │
            │                       │
            │  Delivered to user ✅ │
            └───────────────────────┘
```

---

## 📚 Layer-by-Layer Breakdown

### 1️⃣ Orchestrator Layer
**File**: `RAG/Orchestration/orchestrator.py`

**Responsibilities**:
- Entry point for all queries
- Coordinates workflow between agents
- Manages agent selection based on routing
- Formats final response

**Flow**:
```python
User Query → Orchestrator.run()
           → Router Agent (classify)
           → Needle/Summary Agent (retrieve & answer)
           → Format response
           → Return to user
```

---

### 2️⃣ Router Agent
**File**: `RAG/Agents/router_agent.py`

**Responsibilities**:
- Classify query type using LLM
- Decide between NEEDLE vs SUMMARY routes
- Return routing decision with confidence

**LLM Model**: `gpt-4o-mini`

**Decision Logic**:
```python
NEEDLE:
- Specific facts (phone, date, account number)
- Single atomic piece of information
- Example: "What is Jon Mor's phone number?"

SUMMARY:
- Broad overview required
- Multiple facts synthesized
- Example: "Summarize Jon Mor's entire claim"
```

---

### 3️⃣ Needle Agent
**File**: `RAG/Agents/needle_agent.py`

**Responsibilities**:
- Handle NEEDLE-type queries (specific facts)
- Request retrieval from Index Layer
- Use LLM to extract precise fact from chunks
- Return structured answer or None if not found

**LLM Model**: `gpt-4o-mini`

**Retrieval Settings**:
```python
top_k = 3                  # Retrieve max 3 chunks
similarity_threshold = 0.75  # Minimum similarity score
```

**Policy**: **NO GUESSING** - Returns `None` if fact not found

---

### 4️⃣ Summary Agent
**File**: `RAG/Agents/summary_agent.py`

**Responsibilities**:
- Handle SUMMARY-type queries (broad questions)
- Request retrieval from Index Layer
- Use MapReduce to synthesize comprehensive answer
- Return context-grounded summary

**LLM Model**: `gpt-4o-mini`

**Retrieval Settings**:
```python
top_k = 15  # Retrieve more chunks for comprehensive view
```

**Policy**: **CONTEXT-GROUNDED SYNTHESIS** - Only use retrieved information

---

### 5️⃣ Index Layer ⭐ (THE MAGIC HAPPENS HERE)
**File**: `RAG/Index_Layer/index_layer.py`

**Responsibilities**:
- Embed queries into vectors
- Perform vector similarity search
- Apply filters (threshold + top_k)
- Return relevant chunks

**Components**:

#### A. Embedding Model
```python
Model: text-embedding-3-small (OpenAI)
Dimensions: 1536
Input: Text string
Output: Vector [0.234, -0.456, 0.678, ...]
```

#### B. Vector Database
```python
Storage: LlamaIndex VectorStore
Chunks: All document chunks pre-embedded
Metadata: Claimant names, claim numbers, dates
```

#### C. Similarity Calculation
```python
Method: Cosine Similarity
Formula: similarity = dot(query_vec, chunk_vec) / (||query|| * ||chunk||)
Range: 0.0 (unrelated) to 1.0 (identical)
```

#### D. Filtering Pipeline
```python
Step 1: Calculate similarity for ALL chunks
Step 2: Filter by similarity_threshold (≥ 0.75)
Step 3: Sort by similarity (highest first)
Step 4: Limit to top_k results (3 for NEEDLE, 15 for SUMMARY)
Step 5: Return chunk texts + metadata
```

---

## ⚙️ Key Parameters Explained

### `top_k` (Number of Chunks)
**What it does**: Limits the maximum number of chunks returned

**Current Settings**:
- NEEDLE queries: `top_k = 3` (only need a few for specific facts)
- SUMMARY queries: `top_k = 15` (need more for comprehensive view)

**Analogy**: 
- Low top_k (3) = "Give me the 3 best answers"
- High top_k (15) = "Give me the top 15 to understand the full picture"

**Trade-off**:
- ✅ Lower top_k = More focused, less noise
- ❌ Lower top_k = Might miss relevant info
- ✅ Higher top_k = More comprehensive coverage
- ❌ Higher top_k = More noise, slower processing

---

### `similarity_threshold` (Quality Filter)
**What it does**: Filters out chunks below a certain similarity score

**Current Setting**: `0.75` (75% similarity or higher)

**Similarity Scale**:
```
1.00 - 0.95: Nearly identical meaning ⭐⭐⭐⭐⭐
0.94 - 0.85: Very similar, highly relevant ⭐⭐⭐⭐
0.84 - 0.75: Similar, relevant ⭐⭐⭐
──────────── threshold = 0.75 ────────────
0.74 - 0.65: Somewhat similar ⭐⭐
0.64 - 0.50: Loosely related ⭐
0.49 - 0.00: Not relevant ❌
```

**Analogy**:
- Low threshold (0.7) = "Include anything somewhat relevant"
- High threshold (0.75) = "Only include highly relevant content"

**Trade-off**:
- ✅ Higher threshold = Better precision, less noise
- ❌ Higher threshold = Might filter out useful info
- ✅ Lower threshold = Higher recall, catch more info
- ❌ Lower threshold = More noise, less precision

---

## 💡 Example Walkthrough

### Example Query: "What is Jon Mor's phone number?"

#### Step-by-Step Processing:

**1. User Input**
```
Query: "What is Jon Mor's phone number?"
```

**2. Orchestrator**
```
✓ Receive query
✓ Send to Router Agent
```

**3. Router Agent (LLM Classification)**
```
Input: "What is Jon Mor's phone number?"
LLM Analysis:
  - Contains: "What is..."
  - Asks for: Specific fact (phone number)
  - Type: Single atomic information
  
Decision: NEEDLE
Confidence: 1.0
Reason: "Asks for specific piece of information"
```

**4. Needle Agent**
```
✓ Receive NEEDLE route
✓ Call needle_retriever with query
```

**5. Index Layer - Embedding**
```
Input Text: "What is Jon Mor's phone number?"
Embedding Model: text-embedding-3-small

Output Vector (1536 dims):
[0.234, -0.456, 0.678, 0.123, -0.891, 0.345, ...]
```

**6. Index Layer - Similarity Search**
```
Query Vector: [0.234, -0.456, 0.678, ...]

Calculate similarity with ALL chunks:

Chunk 1: "Jon Mor, Phone: (555) 100-2000"
  Vector: [0.231, -0.451, 0.682, ...]
  Similarity: 0.95 ✅

Chunk 2: "Contact Info: Jon Mor, email..."
  Vector: [0.198, -0.423, 0.701, ...]
  Similarity: 0.82 ✅

Chunk 3: "Claimant: Jon Mor, Account..."
  Vector: [0.241, -0.389, 0.655, ...]
  Similarity: 0.78 ✅

Chunk 4: "Jon Mor vehicle: Toyota..."
  Vector: [0.112, -0.298, 0.544, ...]
  Similarity: 0.68 ❌ (below 0.75)

Chunk 5: "Eli Cohen claim details"
  Vector: [0.034, 0.123, -0.234, ...]
  Similarity: 0.45 ❌ (below 0.75)
```

**7. Index Layer - Apply Filters**
```
Filter 1: similarity_threshold = 0.75
  ✅ Keep: Chunk 1 (0.95)
  ✅ Keep: Chunk 2 (0.82)
  ✅ Keep: Chunk 3 (0.78)
  ❌ Discard: Chunk 4 (0.68)
  ❌ Discard: Chunk 5 (0.45)

Filter 2: top_k = 3
  Result: 3 chunks pass (all kept)

Final: Return Chunk 1, 2, 3
```

**8. Needle Agent - LLM Extraction**
```
LLM Input:
  Question: "What is Jon Mor's phone number?"
  
  Chunks:
  1. "Jon Mor, Phone: (555) 100-2000, Email: ..."
  2. "Contact Information for Jon Mor..."
  3. "Claimant: Jon Mor, Account: ACC9900460..."

LLM Processing:
  - Reads all 3 chunks
  - Finds phone number in Chunk 1
  - Extracts exact value
  
LLM Output:
  Answer: "(555) 100-2000"
  Confidence: 0.95
  Source: chunk_1
```

**9. Orchestrator - Format Response**
```json
{
  "answer": "(555) 100-2000",
  "route": "NEEDLE",
  "confidence": 0.95,
  "sources": ["chunk_1"],
  "retrieved_chunks_content": [
    "Jon Mor, Phone: (555) 100-2000...",
    "Contact Information for Jon Mor...",
    "Claimant: Jon Mor, Account..."
  ]
}
```

**10. Return to User**
```
Final Answer: (555) 100-2000
✓ Correct
✓ Grounded in retrieved data
✓ No hallucination
```

---

## 📊 Performance Metrics

### Current System Performance (RAGAS Evaluation)

| Metric | Score | Meaning |
|--------|-------|---------|
| **Context Recall** | 0.857 | Retrieves 85.7% of needed information |
| **Context Precision** | 0.703 | 70.3% of retrieved chunks are relevant |
| **Faithfulness** | 1.000 | Zero hallucinations - 100% grounded |
| **Answer Relevancy** | 0.846 | 84.6% of answer directly addresses question |

### Retrieval Settings Impact

| Setting | Value | Impact |
|---------|-------|--------|
| `top_k` | 3 | Focused retrieval for specific facts |
| `similarity_threshold` | 0.75 | High-quality chunks only |
| Embedding Model | text-embedding-3-small | Fast, accurate, 1536 dimensions |
| LLM Model | gpt-4o-mini | Cost-effective, reliable |

---

## 🎯 Quick Reference

### When to Adjust Parameters

#### Increase `top_k` if:
- ❌ Missing information in answers
- ❌ Recall is low
- ✅ Need more comprehensive coverage

#### Decrease `top_k` if:
- ❌ Too much noise in responses
- ❌ Precision is low
- ✅ Want more focused answers

#### Increase `similarity_threshold` if:
- ❌ Too many irrelevant chunks
- ❌ Precision is low
- ✅ Want higher quality retrieval

#### Decrease `similarity_threshold` if:
- ❌ Missing relevant information
- ❌ Recall is low
- ✅ Need to cast wider net

---

## 🔧 Configuration Files

### Main Configuration Locations

**Needle Retriever Settings**:
```
File: evaluation-ragas/ragas_eval.py
Lines: ~99-102

needle_retriever = index_manager.get_needle_retriever(
    top_k=3,
    similarity_threshold=0.75,
)
```

**Summary Retriever Settings**:
```
File: evaluation-ragas/ragas_eval.py
Lines: ~103-105

map_reduce_query_engine = index_manager.get_map_reduce_query_engine(
    top_k=15,
)
```

**Embedding Model**:
```
File: RAG/Index_Layer/index_layer.py

Model: text-embedding-3-small (OpenAI)
Dimensions: 1536
```

**LLM Models**:
```
Router Agent: gpt-4o-mini (temperature=0.0)
Needle Agent: gpt-4o-mini (temperature=0.0)
Summary Agent: gpt-4o-mini (temperature=0.2)
```

---

## 📖 Related Documentation

- `RAGAS_ANALYSIS.md` - Detailed evaluation results
- `IMPROVEMENT_GUIDE.md` - Optimization recommendations
- `evaluation-ragas/ragas_results.json` - Raw evaluation data
- `RAG/README.md` - RAG system architecture overview

---

## 🎓 Summary

This RAG system uses a **6-layer architecture** to process queries:

1. **Orchestrator** - Coordinates everything
2. **Router Agent** - Classifies query type
3. **Needle/Summary Agent** - Handles specific query types
4. **Index Layer** - Performs vector search & filtering ⭐
5. **LLM** - Extracts/generates final answer
6. **Response Formatting** - Returns to user

**The magic happens in the Index Layer** where:
- ✅ Queries are embedded into vectors
- ✅ Similarity scores are calculated
- ✅ Filters are applied (threshold + top_k)
- ✅ Best chunks are returned

**Current Performance**: Production-ready with strong metrics across all dimensions.

---

*Last Updated: December 14, 2025*  
*System Version: RAG Agent v2*  
*Evaluation Framework: RAGAS with OpenAI GPT-4o-mini*
