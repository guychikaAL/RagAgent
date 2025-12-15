# RagAgentv2 - Complete Project Overview

## 📋 **Table of Contents**

1. [What is This Project?](#what-is-this-project)
2. [Detailed Version](#detailed-version)
   - [Flow 1: Build Production Index](#flow-1-build-production-index-build-time)
   - [Flow 2: Query Time](#flow-2-query-time-answering-questions)
   - [Evaluation Systems](#evaluation-systems)
3. [Short Version](#short-version)
4. [Overall Project Summary](#overall-project-summary)

---

## 🎯 **What is This Project?**

**RagAgentv2** is a **production-ready Retrieval-Augmented Generation (RAG) system** specifically designed for **insurance claim processing**. It allows users to ask natural language questions about insurance claim documents and receive accurate, grounded answers.

**Core Capabilities:**
- Process multi-claim PDF documents (20+ claims per file)
- Answer atomic questions ("What is Jon Mor's phone?")
- Answer complex questions ("Summarize the claim timeline")
- Perform date calculations using MCP tools ("How many days from accident to repair?")
- Prevent hallucination through strict grounding
- Evaluate system performance with dual evaluation frameworks

---

# 🔄 **FLOWS SECTION**

## **Overview: Two Critical Flows**

The RagAgentv2 system operates through **two distinct flows** that work together to enable fast, accurate question answering:

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  FLOW 1: BUILD PRODUCTION INDEX (One-Time)              │
│  ────────────────────────────────────────────────────   │
│  Raw PDF → Searchable Vector Database                   │
│  Duration: 5-10 minutes                                 │
│  Frequency: Once (or when data changes)                 │
│                                                         │
│                                                         │
│  FLOW 2: QUERY TIME (Every Question)                    │
│  ────────────────────────────────────────────────────   │
│  User Question → Intelligent Answer                     │
│  Duration: 2-5 seconds                                  │
│  Frequency: Every user query                            │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## **FLOW 1: Build Production Index (Build Time)**

### **Complete Flow Diagram:**

```
┌──────────────────────────────────────────────────────────────────────────┐
│                   FLOW 1: BUILD PRODUCTION INDEX                         │
│                      (Run Once - ~5-10 minutes)                          │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  📄 INPUT: auto_claim_20_forms_FINAL.pdf                                │
│            (45 pages, 20 insurance claims)                               │
│                                                                          │
│     ↓                                                                     │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  STAGE 1.1: PDF INGESTION                                       │    │
│  │  ══════════════════════════════════════════════════════════════ │    │
│  │  File: RAG/PDF_Ingestion/pdf_ingestion.py                       │    │
│  │                                                                  │    │
│  │  Process:                                                        │    │
│  │  1. Validate PDF file (exists, readable, not encrypted)         │    │
│  │  2. Extract text from all 45 pages                              │    │
│  │  3. Remove page numbers and artifacts                           │    │
│  │  4. Fix broken line breaks (automo-\nbile → automobile)         │    │
│  │  5. Normalize whitespace and reconstruct paragraphs             │    │
│  │  6. Extract metadata (pages, words, dates, etc.)                │    │
│  │  7. Create LlamaIndex Document object                           │    │
│  │                                                                  │    │
│  │  Output: 1 Document (clean text + metadata)                     │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│     ↓                                                                     │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  STAGE 1.2: CLAIM SEGMENTATION                                  │    │
│  │  ══════════════════════════════════════════════════════════════ │    │
│  │  File: RAG/Claim_Segmentation/claim_segmentation.py             │    │
│  │                                                                  │    │
│  │  Process:                                                        │    │
│  │  1. Detect claim boundaries ("AUTO CLAIM FORM #N")              │    │
│  │  2. Extract text slice for each claim                           │    │
│  │  3. Extract claimant name dynamically (e.g., "Jon Mor")         │    │
│  │  4. Generate unique claim_id for each claim                     │    │
│  │  5. Add claim-specific metadata                                 │    │
│  │  6. Create separate Document for each claim                     │    │
│  │                                                                  │    │
│  │  Output: 20 Documents (one per claim)                           │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│     ↓                                                                     │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  STAGE 1.3: CHUNKING LAYER                                      │    │
│  │  ══════════════════════════════════════════════════════════════ │    │
│  │  File: RAG/Chunking_Layer/chunking_layer.py                     │    │
│  │                                                                  │    │
│  │  Process:                                                        │    │
│  │  1. Detect sections (SECTION N – TITLE patterns)                │    │
│  │     └─ Create IndexNode for each section                        │    │
│  │                                                                  │    │
│  │  2. Create parent chunks (~800 characters each)                 │    │
│  │     └─ Prepend claim context to each parent                     │    │
│  │     └─ Create TextNode for each parent                          │    │
│  │                                                                  │    │
│  │  3. Create child chunks (~200 characters each)                  │    │
│  │     └─ Split parents into smaller chunks                        │    │
│  │     └─ Create TextNode for each child                           │    │
│  │                                                                  │    │
│  │  4. Link relationships (section → parent → child)               │    │
│  │                                                                  │    │
│  │  5. Enrich metadata (chunk_id, claim_id, position, etc.)        │    │
│  │                                                                  │    │
│  │  Hierarchy: 3 Levels                                            │    │
│  │  • Sections: Navigational structure                             │    │
│  │  • Parents: Broad context (~800 chars)                          │    │
│  │  • Children: Precise facts (~200 chars)                         │    │
│  │                                                                  │    │
│  │  Output: ~550 Hierarchical Nodes                                │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│     ↓                                                                     │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  STAGE 1.4: INDEX LAYER                                         │    │
│  │  ══════════════════════════════════════════════════════════════ │    │
│  │  File: RAG/Index_Layer/index_layer.py                           │    │
│  │                                                                  │    │
│  │  Process:                                                        │    │
│  │  1. Initialize embedding model                                  │    │
│  │     • Model: text-embedding-3-small                             │    │
│  │     • Dimension: 1536                                           │    │
│  │     • CRITICAL: Same model for build AND query                  │    │
│  │                                                                  │    │
│  │  2. Embed all 550 nodes                                         │    │
│  │     • API call for each node → 1536-dim vector                  │    │
│  │     • Vectors capture semantic meaning                          │    │
│  │     • Main time cost: ~5 minutes (API calls)                    │    │
│  │                                                                  │    │
│  │  3. Build FAISS vector store                                    │    │
│  │     • Fast similarity search index                              │    │
│  │     • Stores embeddings + metadata                              │    │
│  │     • Enables sub-second retrieval                              │    │
│  │                                                                  │    │
│  │  4. Create storage context                                      │    │
│  │     • docstore: Original node texts                             │    │
│  │     • vector_store: Embeddings                                  │    │
│  │     • index_store: Relationships                                │    │
│  │                                                                  │    │
│  │  5. Build VectorStoreIndex                                      │    │
│  │     • Combines vector store + storage                           │    │
│  │     • Handles query-time search                                 │    │
│  │                                                                  │    │
│  │  6. Build SummaryIndex                                          │    │
│  │     • For comprehensive retrieval (no filtering)                │    │
│  │     • Used by MapReduce                                         │    │
│  │                                                                  │    │
│  │  7. Create retrievers                                           │    │
│  │     • Needle Retriever: top_k=3, threshold=0.75                 │    │
│  │       → For atomic questions (high precision)                   │    │
│  │     • MapReduce Engine: top_k=15                                │    │
│  │       → For complex questions (high recall)                     │    │
│  │                                                                  │    │
│  │  8. Save to disk                                                │    │
│  │     • production_index/docstore.json                            │    │
│  │     • production_index/vector_store.json                        │    │
│  │     • production_index/index_store.json                         │    │
│  │     • production_index/default__vector_store.json               │    │
│  │                                                                  │    │
│  │  Output: production_index/ folder                               │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│     ↓                                                                     │
│  💾 OUTPUT: production_index/ (ready for query time!)                   │
│                                                                          │
│  ✅ RESULT:                                                              │
│     • 550 embedded nodes stored in FAISS                                │
│     • Fast similarity search enabled                                    │
│     • Ready to answer questions in seconds                              │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

### **Flow 1 Stage Summary:**

| Stage | File | Input | Output | Duration |
|-------|------|-------|--------|----------|
| 1.1 PDF Ingestion | `pdf_ingestion.py` | PDF file | 1 Document | ~30 sec |
| 1.2 Claim Segmentation | `claim_segmentation.py` | 1 Document | 20 Documents | ~5 sec |
| 1.3 Chunking | `chunking_layer.py` | 20 Documents | 550 Nodes | ~10 sec |
| 1.4 Indexing | `index_layer.py` | 550 Nodes | production_index/ | ~5-10 min |
| **Total** | | **PDF** | **Searchable Index** | **~5-10 min** |

---

## **FLOW 2: Query Time (Answering Questions)**

### **Complete Flow Diagram:**

```
┌──────────────────────────────────────────────────────────────────────────┐
│                     FLOW 2: QUERY TIME                                   │
│                 (Every Question - ~2-5 seconds)                          │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  💬 INPUT: User Question                                                │
│            "What is Jon Mor's phone number?"                             │
│                                                                          │
│     ↓                                                                     │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  STAGE 2.1: LOAD PRODUCTION INDEX                               │    │
│  │  ══════════════════════════════════════════════════════════════ │    │
│  │  File: main.py → index_layer.py                                 │    │
│  │                                                                  │    │
│  │  Process:                                                        │    │
│  │  1. Read production_index/ folder from disk                     │    │
│  │  2. Load docstore.json (node texts)                             │    │
│  │  3. Load vector_store.json (embeddings)                         │    │
│  │  4. Load index_store.json (relationships)                       │    │
│  │  5. Reconstruct FAISS index in memory                           │    │
│  │  6. Recreate VectorStoreIndex                                   │    │
│  │  7. Recreate SummaryIndex                                       │    │
│  │  8. Initialize embedding model (SAME as build time)             │    │
│  │                                                                  │    │
│  │  Duration: ~2 seconds (no API calls, just file loading)         │    │
│  │                                                                  │    │
│  │  Output: Index loaded in memory, ready for queries              │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│     ↓                                                                     │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  STAGE 2.2: INITIALIZE AGENTS                                   │    │
│  │  ══════════════════════════════════════════════════════════════ │    │
│  │  File: main.py                                                  │    │
│  │                                                                  │    │
│  │  Process:                                                        │    │
│  │  1. Create Router Agent                                         │    │
│  │     • LLM: gpt-4o-mini, temp=0.0                                │    │
│  │     • Purpose: Classify question type                           │    │
│  │     • Output: "needle" or "summary" route                       │    │
│  │                                                                  │    │
│  │  2. Create Needle Agent                                         │    │
│  │     • LLM: gpt-4o-mini, temp=0.0                                │    │
│  │     • Purpose: Extract atomic facts                             │    │
│  │     • Features: MCP tools enabled, null-safe                    │    │
│  │                                                                  │    │
│  │  3. Create Summary Agent                                        │    │
│  │     • LLM: gpt-4o-mini, temp=0.2                                │    │
│  │     • Purpose: Synthesize comprehensive answers                 │    │
│  │     • Features: MCP tools enabled, MapReduce support            │    │
│  │                                                                  │    │
│  │  4. Get retrievers from Index Layer                             │    │
│  │     • Needle Retriever (top_k=3, threshold=0.75)                │    │
│  │     • MapReduce Query Engine (top_k=15)                         │    │
│  │                                                                  │    │
│  │  Duration: <1 second (LLM initialization)                       │    │
│  │                                                                  │    │
│  │  Output: Three agents ready, retrievers configured              │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│     ↓                                                                     │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  STAGE 2.3: ORCHESTRATOR INITIALIZATION                         │    │
│  │  ══════════════════════════════════════════════════════════════ │    │
│  │  File: main.py → orchestrator.py                                │    │
│  │                                                                  │    │
│  │  Process:                                                        │    │
│  │  1. Inject all dependencies                                     │    │
│  │     • Router Agent                                              │    │
│  │     • Needle Agent                                              │    │
│  │     • Summary Agent                                             │    │
│  │     • Needle Retriever                                          │    │
│  │     • MapReduce Engine                                          │    │
│  │                                                                  │    │
│  │  2. Validate all components present                             │    │
│  │                                                                  │    │
│  │  3. Create orchestrator instance                                │    │
│  │     • Pure coordinator (no business logic)                      │    │
│  │     • Stateless (no memory between queries)                     │    │
│  │                                                                  │    │
│  │  Duration: <1 second                                            │    │
│  │                                                                  │    │
│  │  Output: Orchestrator ready to handle queries                   │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│     ↓                                                                     │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  STAGE 2.4: QUERY PREPROCESSING                                 │    │
│  │  ══════════════════════════════════════════════════════════════ │    │
│  │  File: orchestrator.py (run method)                             │    │
│  │                                                                  │    │
│  │  Process:                                                        │    │
│  │  1. Analyze user question for claim identifiers                 │    │
│  │                                                                  │    │
│  │  2. Extract claim number (if present)                           │    │
│  │     • Patterns: "claim #5", "form number 5"                     │    │
│  │     • Result: claim_number = "5"                                │    │
│  │                                                                  │    │
│  │  3. Extract claimant name (if present)                          │    │
│  │     • Pattern: Capitalized first + last name                    │    │
│  │     • Example: "Jon Mor's phone" → "Jon Mor"                    │    │
│  │     • Result: claimant_name = "Jon Mor"                         │    │
│  │                                                                  │    │
│  │  4. Create PostFilterRetriever (if needed)                      │    │
│  │     • If claim identifier detected:                             │    │
│  │       → Wrap base retriever                                     │    │
│  │       → Retrieve 3x more results                                │    │
│  │       → Filter by metadata (claim_number OR claimant_name)      │    │
│  │       → Return top_k after filtering                            │    │
│  │     • Why: FAISS doesn't support native metadata filtering      │    │
│  │                                                                  │    │
│  │  Duration: <100ms                                               │    │
│  │                                                                  │    │
│  │  Output: Filtered or default retriever ready                    │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│     ↓                                                                     │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  STAGE 2.5: ROUTING DECISION                                    │    │
│  │  ══════════════════════════════════════════════════════════════ │    │
│  │  File: orchestrator.py → router_agent.py                        │    │
│  │                                                                  │    │
│  │  Process:                                                        │    │
│  │  1. Send question to Router Agent                               │    │
│  │                                                                  │    │
│  │  2. Router LLM analyzes question intent                         │    │
│  │     • No retrieval at this stage (pure classification)          │    │
│  │                                                                  │    │
│  │  3. Classification logic:                                       │    │
│  │     • NEEDLE: Single specific fact needed                       │    │
│  │       Examples: "What's the phone?", "When accident?"           │    │
│  │       Also: Date calculations ("How many days?")                │    │
│  │                                                                  │    │
│  │     • SUMMARY: Multiple facts or explanation                    │    │
│  │       Examples: "Summarize claim", "What happened?"             │    │
│  │                                                                  │    │
│  │  4. Return route decision                                       │    │
│  │     • route: "needle" or "summary"                              │    │
│  │     • confidence: 0.0 to 1.0                                    │    │
│  │     • reason: Explanation                                       │    │
│  │                                                                  │    │
│  │  Example for "What is Jon Mor's phone?":                        │    │
│  │     route = "needle"                                            │    │
│  │     confidence = 0.95                                           │    │
│  │     reason = "Asks for single specific fact"                    │    │
│  │                                                                  │    │
│  │  Duration: ~500ms (LLM API call)                                │    │
│  │                                                                  │    │
│  │  Output: Routing decision (which agent to use)                  │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│     ↓                                                                     │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  STAGE 2.6a: NEEDLE AGENT EXECUTION (if route = "needle")       │    │
│  │  ══════════════════════════════════════════════════════════════ │    │
│  │  File: orchestrator.py → needle_agent.py                        │    │
│  │                                                                  │    │
│  │  Process:                                                        │    │
│  │  1. RETRIEVAL                                                   │    │
│  │     • Use Needle Retriever (top_k=3, threshold=0.75)            │    │
│  │     • Embed user question                                       │    │
│  │     • Cosine similarity search in FAISS                         │    │
│  │     • Return 3 most similar chunks (if above threshold)         │    │
│  │     • Chunks are ~200 chars (child chunks)                      │    │
│  │                                                                  │    │
│  │  2. CONTEXT PREPARATION                                         │    │
│  │     • Format chunks for LLM                                     │    │
│  │     • Include metadata (claim_id, claimant_name)                │    │
│  │                                                                  │    │
│  │  3a. STANDARD PATH (No date calculation)                        │    │
│  │      • Send question + chunks to Needle LLM                     │    │
│  │      • LLM extracts exact answer                                │    │
│  │      • Returns structured response                              │    │
│  │                                                                  │    │
│  │  3b. MCP TOOL PATH (Date calculation needed)                    │    │
│  │      • LLM recognizes date calculation in question              │    │
│  │      • Extracts dates from chunks                               │    │
│  │      • Tool Call Decision (tool_choice="auto"):                 │    │
│  │        → LLM: "I see two dates, call calculate_days_between"    │    │
│  │      • Tool Execution:                                          │    │
│  │        → calculate_days_between("2024-01-24", "2024-02-18")     │    │
│  │        → Python datetime performs exact calculation             │    │
│  │        → Returns: {"success": True, "number_of_days": 25}       │    │
│  │      • Final Answer Formation:                                  │    │
│  │        → LLM receives tool result                               │    │
│  │        → Formats: "25 days passed between..."                   │    │
│  │                                                                  │    │
│  │  4. RESPONSE FORMATION                                          │    │
│  │     • answer: Extracted fact or "null"                          │    │
│  │     • confidence: 1.0 if found, 0.0 if not                      │    │
│  │     • sources: List of chunk IDs                                │    │
│  │     • reason: Explanation (mentions MCP if used)                │    │
│  │                                                                  │    │
│  │  Example Response:                                              │    │
│  │     answer = "555-1234"                                         │    │
│  │     confidence = 1.0                                            │    │
│  │     sources = ["chunk_abc123"]                                  │    │
│  │     reason = "Found in contact section"                         │    │
│  │                                                                  │    │
│  │  Duration: ~1-2 seconds (retrieval + LLM)                       │    │
│  │                                                                  │    │
│  │  Output: Precise answer with high confidence                    │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│     │                                                                    │
│     OR                                                                   │
│     │                                                                    │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  STAGE 2.6b: SUMMARY AGENT EXECUTION (if route = "summary")     │    │
│  │  ══════════════════════════════════════════════════════════════ │    │
│  │  File: orchestrator.py → summary_agent.py                       │    │
│  │                                                                  │    │
│  │  Process (MapReduce Approach):                                  │    │
│  │                                                                  │    │
│  │  1. RETRIEVAL PHASE                                             │    │
│  │     • Use MapReduce Query Engine                                │    │
│  │     • Retrieve top_k=15 chunks (comprehensive)                  │    │
│  │     • Uses both parent and child chunks                         │    │
│  │     • No similarity threshold (high recall)                     │    │
│  │                                                                  │    │
│  │  2. MAP PHASE                                                   │    │
│  │     • For each of 15 retrieved chunks:                          │    │
│  │       → LLM generates summary of that chunk                     │    │
│  │       → Focuses on question-relevant information                │    │
│  │     • Results in 15 mini-summaries                              │    │
│  │                                                                  │    │
│  │  3. REDUCE PHASE                                                │    │
│  │     • LLM combines all mini-summaries                           │    │
│  │     • Synthesizes coherent final answer                         │    │
│  │     • Resolves contradictions                                   │    │
│  │     • Organizes information logically                           │    │
│  │                                                                  │    │
│  │  4. MCP TOOL INTEGRATION (if needed)                            │    │
│  │     • During synthesis, LLM may recognize date calculation      │    │
│  │     • Calls calculate_days_between with dates from context      │    │
│  │     • Incorporates exact calculation in final answer            │    │
│  │                                                                  │    │
│  │  5. RESPONSE FORMATION                                          │    │
│  │     • answer: Comprehensive synthesized response                │    │
│  │     • confidence: 0.8-0.9 (synthesis less certain)              │    │
│  │     • sources: All chunk IDs used (15+)                         │    │
│  │     • reason: Explanation of synthesis                          │    │
│  │                                                                  │    │
│  │  Example Response:                                              │    │
│  │     answer = "Jon Mor filed a claim on Jan 26, 2024,            │    │
│  │               following an accident on Jan 24, 2024..."         │    │
│  │     confidence = 0.9                                            │    │
│  │     sources = [15+ chunk IDs]                                   │    │
│  │     reason = "Synthesized from incident and payment sections"   │    │
│  │                                                                  │    │
│  │  Duration: ~2-4 seconds (retrieval + multiple LLM calls)        │    │
│  │                                                                  │    │
│  │  Output: Comprehensive answer with broad context                │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│     ↓                                                                     │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  STAGE 2.7: RESPONSE NORMALIZATION                              │    │
│  │  ══════════════════════════════════════════════════════════════ │    │
│  │  File: orchestrator.py (run method)                             │    │
│  │                                                                  │    │
│  │  Process:                                                        │    │
│  │  1. Combine routing metadata + agent result                     │    │
│  │                                                                  │    │
│  │  2. Create unified response structure:                          │    │
│  │     {                                                            │    │
│  │       "route": "needle" or "summary",                           │    │
│  │       "answer": "555-1234",                                     │    │
│  │       "confidence": 1.0,                                        │    │
│  │       "sources": ["chunk_abc123", ...],                         │    │
│  │       "retrieved_chunks_content": ["Phone: 555-1234", ...],     │    │
│  │       "reason": "Found in contact section"                      │    │
│  │     }                                                            │    │
│  │                                                                  │    │
│  │  3. Log results:                                                │    │
│  │     • Print route decision                                      │    │
│  │     • Print final answer                                        │    │
│  │     • Print confidence score                                    │    │
│  │     • Print number of sources                                   │    │
│  │     • Print reasoning                                           │    │
│  │                                                                  │    │
│  │  Duration: <100ms                                               │    │
│  │                                                                  │    │
│  │  Output: Standardized response for external consumers           │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│     ↓                                                                     │
│  ✅ OUTPUT: Final Answer                                                │
│            "555-1234"                                                    │
│                                                                          │
│  📊 TOTAL TIME: ~2-5 seconds (fast!)                                    │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

### **Flow 2 Stage Summary:**

| Stage | File | Purpose | Duration |
|-------|------|---------|----------|
| 2.1 Load Index | `index_layer.py` | Load pre-built index from disk | ~2 sec |
| 2.2 Initialize Agents | `main.py` | Create Router, Needle, Summary agents | <1 sec |
| 2.3 Orchestrator Init | `orchestrator.py` | Create central coordinator | <1 sec |
| 2.4 Query Preprocessing | `orchestrator.py` | Extract claim identifiers, create filters | <100ms |
| 2.5 Routing | `router_agent.py` | Classify question (needle/summary) | ~500ms |
| 2.6a Needle Execution | `needle_agent.py` | Extract atomic fact (+ MCP if needed) | ~1-2 sec |
| 2.6b Summary Execution | `summary_agent.py` | Synthesize comprehensive answer (MapReduce) | ~2-4 sec |
| 2.7 Response Normalization | `orchestrator.py` | Format unified response | <100ms |
| **Total** | | **Question → Answer** | **~2-5 sec** |

---

### **Flow 2 Decision Tree:**

```
User Question
    ↓
Load Index → Initialize Agents → Orchestrator
    ↓
Query Preprocessing
    ├─ Claim Number? → Filter by claim_number
    ├─ Claimant Name? → Filter by claimant_name
    └─ No identifier → Use default retriever
    ↓
Routing Decision
    ├─ Route = NEEDLE
    │   ↓
    │   Needle Agent
    │   ├─ Retrieve 3 chunks (threshold=0.75)
    │   ├─ Date calculation needed?
    │   │   ├─ YES → Call MCP tool → Format answer
    │   │   └─ NO → Extract fact → Return answer
    │   └─ Return precise answer
    │
    └─ Route = SUMMARY
        ↓
        Summary Agent
        ├─ Retrieve 15 chunks (no threshold)
        ├─ Map Phase: Summarize each chunk
        ├─ Reduce Phase: Combine summaries
        ├─ Date calculation needed?
        │   ├─ YES → Call MCP tool → Incorporate in answer
        │   └─ NO → Return synthesized answer
        └─ Return comprehensive answer
    ↓
Response Normalization
    ↓
Final Answer to User
```

---

### **Key Differences Between Flows:**

```
┌─────────────────────────────────────────────────────────┐
│         FLOW 1 vs. FLOW 2 COMPARISON                    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  FLOW 1 (Build Index):                                  │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│  • When: Once (or when data changes)                    │
│  • Duration: 5-10 minutes                               │
│  • Main Cost: Embedding API calls (550 chunks)          │
│  • Output: production_index/ folder on disk             │
│  • Purpose: Prepare data for fast retrieval             │
│  • Stages: 4 (Ingest → Segment → Chunk → Index)        │
│                                                         │
│                                                         │
│  FLOW 2 (Query Time):                                   │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│  • When: Every user question                            │
│  • Duration: 2-5 seconds                                │
│  • Main Cost: LLM API calls (1-3 per query)             │
│  • Output: Natural language answer                      │
│  • Purpose: Answer questions fast                       │
│  • Stages: 7 (Load → Init → Route → Execute → Answer)  │
│                                                         │
│                                                         │
│  WHY THIS DESIGN:                                       │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│  ✅ Efficiency: Build once, query many times            │
│  ✅ Speed: Query time is fast (no re-embedding)         │
│  ✅ Cost: Embedding cost paid once, not per query       │
│  ✅ Scalability: Supports concurrent users              │
│  ✅ Production-Ready: Proven architecture pattern       │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

# 📖 **Detailed Version**

## **System Architecture: Two Flows**

```
┌─────────────────────────────────────────────────────────┐
│                TWO DISTINCT FLOWS                       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  FLOW 1: BUILD PRODUCTION INDEX                         │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│  When: Once (or when data changes)                      │
│  File: build_production_index.py                        │
│  Purpose: Transform PDF → Searchable Index              │
│  Duration: ~5-10 minutes                                │
│  Output: production_index/ folder                       │
│                                                         │
│                                                         │
│  FLOW 2: QUERY TIME                                     │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│  When: Every user question                              │
│  File: main.py                                          │
│  Purpose: Answer questions using pre-built index        │
│  Duration: 2-5 seconds per question                     │
│  Output: Natural language answer                        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## **Flow 1: Build Production Index (Build Time)**

**Purpose:** Transform a raw PDF document into a searchable, embedded vector database that enables fast, accurate retrieval.

**File:** `build_production_index.py`

**When to Run:** Once initially, then again only when:
- New PDF data is added
- Existing data changes
- Index configuration needs updating

---

### **Stage 1.1: PDF Ingestion**

**Location:** `RAG/PDF_Ingestion/pdf_ingestion.py`

**What it does:**
Converts raw PDF files into clean, normalized text documents ready for processing.

**Detailed Process:**

1. **File Validation:**
   - Checks PDF exists and is readable
   - Verifies file size (< 100MB)
   - Ensures not encrypted
   - Validates .pdf extension

2. **Text Extraction:**
   - Opens PDF with pypdf library
   - Extracts text from all pages (45 pages in our case)
   - Removes page numbers and artifacts
   - Fixes broken line breaks (e.g., "automo-\nbile" → "automobile")

3. **Text Normalization:**
   - Removes control characters (form feeds, carriage returns)
   - Normalizes whitespace (multiple spaces → single space)
   - Reconstructs paragraphs (joins lines within paragraphs)
   - Collapses multiple newlines

4. **Metadata Extraction:**
   - Generates deterministic document_id (hash-based)
   - Extracts title (from first line or filename)
   - Counts pages, words, paragraphs
   - Detects dates and times in document
   - Calculates numeric density (helps identify tables vs. prose)
   - Detects heading structure

5. **Document Creation:**
   - Creates LlamaIndex Document object
   - Attaches clean text
   - Attaches metadata
   - Sets deterministic ID

**Output:** Single `Document` object with clean text and metadata

**Why Important:** Clean, normalized text is critical for accurate chunking and retrieval. Bad text extraction = bad retrieval.

---

### **Stage 1.2: Claim Segmentation**

**Location:** `RAG/Claim_Segmentation/claim_segmentation.py`

**What it does:**
Splits one PDF containing multiple insurance claims into separate documents, one per claim.

**Detailed Process:**

1. **Boundary Detection:**
   - Scans document for claim markers
   - Primary pattern: "AUTO CLAIM FORM #N"
   - Fallback patterns: "Claim Number:", section headers
   - Records position of each boundary in the text

2. **Text Slicing:**
   - For each detected boundary:
     - Start position = boundary location
     - End position = next boundary (or end of document)
   - Extracts text slice for each claim

3. **Claimant Name Extraction (Dynamic):**
   - Looks for "Name: FirstName LastName" pattern
   - Extracts from first 500 characters of claim
   - Handles various formats (with/without newlines)
   - NO hardcoding - extracted dynamically from document

4. **Metadata Enrichment:**
   - Generates unique claim_id (hash-based)
   - Adds claim_number (from form)
   - Adds claimant_name (extracted)
   - Inherits parent document metadata
   - Adds claim-specific statistics

5. **Document Creation:**
   - Creates separate Document for each claim
   - Each claim becomes independent processing unit

**Input:** 1 Document (entire PDF)
**Output:** 20 Documents (one per claim)

**Why Important:** Insurance claims are independent business entities. Mixing claims during retrieval causes hallucination ("Jon Mor's phone" should never retrieve Jane Smith's phone). Segmentation ensures claim-level isolation.

---

### **Stage 1.3: Chunking Layer**

**Location:** `RAG/Chunking_Layer/chunking_layer.py`

**What it does:**
Transforms each claim document into a **3-level hierarchical structure** optimized for different retrieval strategies.

**Detailed Process:**

1. **Section Detection:**
   - Detects major sections using heuristic patterns
   - Looks for: "SECTION N – TITLE" patterns
   - Common sections: Claimant Info, Incident Details, Vehicle Info, etc.
   - Creates IndexNode for each section (navigational structure)

2. **Parent Chunking:**
   - Splits each section into ~800-character parent chunks
   - Maintains semantic coherence (doesn't break mid-sentence)
   - Prepends claim context to each parent chunk
   - Example context: "Claim #1 (Jon Mor) - Claimant Information:"
   - Creates TextNode for each parent chunk

3. **Child Chunking:**
   - Further splits each parent into ~200-character child chunks
   - More granular for precise retrieval
   - Inherits parent context
   - Creates TextNode for each child chunk

4. **Relationship Linking:**
   - Links sections to their parent chunks
   - Links parent chunks to their child chunks
   - Maintains hierarchical references in metadata

5. **Metadata Enrichment:**
   - Each node gets:
     - chunk_id (unique identifier)
     - claim_id (which claim it belongs to)
     - claimant_name (for filtering)
     - chunk_type (section/parent/child)
     - position (order in document)
     - parent_id, section_id (hierarchy)
     - semantic_features (section name, etc.)

**Hierarchy Example:**
```
Claim #1 (Jon Mor)
  └─ Section: Claimant Information [IndexNode]
      └─ Parent Chunk 1: "Claim #1 (Jon Mor) - Claimant Information: Name: Jon Mor..." [TextNode]
          ├─ Child Chunk 1.1: "Name: Jon Mor, Phone: 555-1234" [TextNode]
          └─ Child Chunk 1.2: "Address: 123 Main St" [TextNode]
      └─ Parent Chunk 2: "Claim #1 (Jon Mor) - Claimant Information: Account Number..." [TextNode]
          ├─ Child Chunk 2.1: "Account: 123456" [TextNode]
          └─ Child Chunk 2.2: "Email: jon@example.com" [TextNode]
```

**Input:** 20 Claim Documents
**Output:** ~550 Hierarchical Nodes (sections, parents, children)

**Why Important:** Different questions need different granularity. Atomic questions ("What's the phone?") need small, precise chunks (children). Complex questions ("Summarize the claim") need broader context (parents + children). Hierarchy enables both.

---

### **Stage 1.4: Index Layer**

**Location:** `RAG/Index_Layer/index_layer.py`

**What it does:**
Converts hierarchical nodes into searchable vector embeddings and builds FAISS indexes for fast similarity search.

**Detailed Process:**

1. **Embedding Model Initialization:**
   - Creates single OpenAIEmbedding instance
   - Model: `text-embedding-3-small`
   - Dimension: 1536
   - **Critical Rule:** Same embedding model for build AND query
   - Why: Different models produce incompatible vector spaces

2. **Node Embedding:**
   - For each of 550 nodes:
     - Send node text to OpenAI embedding API
     - Receive 1536-dimensional vector
     - Vector represents semantic meaning of text
   - Batch processing for efficiency
   - API calls are main time cost (~5 minutes)

3. **FAISS Vector Store Creation:**
   - Creates FAISS index (Facebook AI Similarity Search)
   - Index type: Flat (exact search, not approximate)
   - Stores: vector embeddings + metadata
   - In-memory structure, persisted to disk
   - Enables fast cosine similarity search

4. **Storage Context Creation:**
   - Creates docstore (stores original node text)
   - Creates index_store (stores node relationships)
   - Creates vector_store (stores embeddings)
   - All three components work together

5. **VectorStoreIndex Building:**
   - Combines vector store + storage context
   - Creates LlamaIndex VectorStoreIndex
   - Handles query-time embedding + search
   - Returns similar nodes for any query

6. **SummaryIndex Building:**
   - Creates separate index for comprehensive retrieval
   - Uses all nodes (no similarity filtering)
   - Used for MapReduce summarization

7. **Retriever Creation:**
   - **Needle Retriever:**
     - Configuration: top_k=3, similarity_threshold=0.75
     - Retrieves few, highly relevant chunks
     - For atomic questions ("What's the phone?")
     - High precision, low recall
   
   - **Summary Retriever:**
     - Configuration: top_k=8, no threshold
     - Retrieves more chunks for context
     - For complex questions
     - High recall, moderate precision

8. **MapReduce Query Engine Creation:**
   - Uses SummaryIndex
   - Retrieves many chunks (top_k=15)
   - Hierarchical summarization:
     - Map: Summarize each chunk individually
     - Reduce: Combine summaries into final answer
   - For comprehensive questions

9. **Persistence:**
   - Saves to `production_index/` folder:
     - `docstore.json` (node texts)
     - `vector_store.json` (embeddings)
     - `index_store.json` (relationships)
     - `default__vector_store.json` (FAISS index)

**Input:** 550 Hierarchical Nodes
**Output:** 
- `production_index/` folder on disk
- Ready for fast query-time loading

**Why Important:** Embeddings transform text into mathematical vectors that capture semantic similarity. "Phone number" and "contact info" have similar vectors even with different words. FAISS enables sub-second retrieval from 550 chunks.

---

### **Flow 1 Summary:**

```
PDF File (45 pages, 20 claims)
    ↓
[PDF Ingestion]
    → Clean text + metadata
    ↓
[Claim Segmentation]
    → 20 separate claim documents
    ↓
[Chunking Layer]
    → 550 hierarchical nodes (sections, parents, children)
    ↓
[Index Layer]
    → 550 embedded vectors + FAISS index
    ↓
production_index/ folder
    → Ready for query time!
```

**Result:** A pre-built, optimized index that enables fast, accurate retrieval for any user question.

---

## **Flow 2: Query Time (Answering Questions)**

**Purpose:** Use the pre-built index to answer user questions quickly and accurately.

**File:** `main.py`

**When to Run:** Every time a user asks a question (can handle many concurrent users).

---

### **Stage 2.1: Load Production Index**

**Location:** `main.py` → `index_layer.py`

**What it does:**
Loads the pre-built index from disk into memory for fast retrieval.

**Detailed Process:**

1. **Index Loading:**
   - Reads from `production_index/` folder
   - Loads docstore.json (node texts)
   - Loads vector_store.json (embeddings)
   - Loads index_store.json (relationships)
   - Reconstructs FAISS index in memory

2. **Storage Context Recreation:**
   - Recreates docstore
   - Recreates vector_store
   - Recreates index_store
   - Links all components

3. **Index Reconstruction:**
   - Recreates VectorStoreIndex
   - Recreates SummaryIndex
   - Both reference same underlying storage

4. **Embedding Model Initialization:**
   - Creates same OpenAIEmbedding instance as build time
   - **Critical:** Must be SAME model as used during building
   - Model: `text-embedding-3-small`
   - Used to embed user queries

**Duration:** ~2 seconds (much faster than building!)

**Why Fast:** No API calls needed. Just loading files from disk and reconstructing in-memory structures.

---

### **Stage 2.2: Initialize Agents**

**Location:** `main.py`

**What it does:**
Creates the three AI agents that power the RAG system.

**Detailed Process:**

1. **Router Agent Initialization:**
   - LLM: OpenAI gpt-4o-mini
   - Temperature: 0.0 (deterministic)
   - Purpose: Classify question type
   - Output: "needle" or "summary" route
   - System prompt includes classification rules:
     - NEEDLE: Atomic facts, specific data, date calculations
     - SUMMARY: Complex questions, explanations, timelines

2. **Needle Agent Initialization:**
   - LLM: OpenAI gpt-4o-mini
   - Temperature: 0.0 (precise facts)
   - Purpose: Extract atomic facts from context
   - Features:
     - Structured output (Pydantic models)
     - MCP tools enabled (for date calculations)
     - Null-safe (can return null if not found)
   - System prompt: Extract exact answer, no guessing

3. **Summary Agent Initialization:**
   - LLM: OpenAI gpt-4o-mini
   - Temperature: 0.2 (slightly creative for synthesis)
   - Purpose: Synthesize comprehensive answers
   - Features:
     - MCP tools enabled
     - Works with MapReduce query engine
     - Combines multiple chunks into coherent answer
   - System prompt: Synthesize from all relevant context

4. **Retriever Creation:**
   - Gets Needle Retriever (top_k=3, threshold=0.75)
   - Gets MapReduce Query Engine (for summaries)
   - Both configured by Index Layer

**Why Multiple Agents:** Different question types need different strategies. Atomic questions need precision, complex questions need comprehensiveness.

---

### **Stage 2.3: Orchestrator Initialization**

**Location:** `main.py` → `orchestrator.py`

**What it does:**
Creates the central coordinator that manages the entire query pipeline.

**Detailed Process:**

1. **Dependency Injection:**
   - Receives all agents (router, needle, summary)
   - Receives all retrievers (needle_retriever, map_reduce_engine)
   - Stores references but doesn't create anything
   - Pure coordinator, no business logic

2. **Validation:**
   - Ensures all required components present
   - Validates at least one summary method available
   - Prints initialization summary

**Why Important:** Orchestrator is the single entry point. It coordinates all components but doesn't do the actual work. Clean separation of concerns.

---

### **Stage 2.4: Query Preprocessing**

**Location:** `orchestrator.py` → `run()` method

**What it does:**
Analyzes the user's question to detect claim-specific queries that need filtering.

**Detailed Process:**

1. **Claim Number Extraction:**
   - Regex patterns:
     - "claim number 5" → "5"
     - "claim #5" → "5"
     - "form #5" → "5"
     - "AUTO CLAIM FORM #5" → "5"

2. **Claimant Name Extraction:**
   - Regex pattern: Capitalized first and last names
   - Examples:
     - "Jon Mor's phone" → "Jon Mor"
     - "What is Jane Smith's address?" → "Jane Smith"

3. **PostFilterRetriever Creation (if needed):**
   - If claim number or name detected:
     - Wraps base retriever
     - Retrieves 3x more results (e.g., 15 instead of 5)
     - Filters by metadata (claim_number OR claimant_name)
     - Returns top_k after filtering
   - Why needed: FAISS doesn't support native metadata filtering
   - Trade-off: Retrieve more, filter in Python

**Example:**
```
Question: "What is Jon Mor's phone number?"
→ Extracts: claimant_name = "Jon Mor"
→ Creates filtered retriever
→ Retrieval only searches Jon Mor's chunks
```

**Why Important:** Prevents cross-claim contamination. "Jon Mor's phone" should never return Jane Smith's phone number, even if semantically similar.

---

### **Stage 2.5: Routing Decision**

**Location:** `orchestrator.py` → Router Agent

**What it does:**
Classifies the question to determine which agent should handle it.

**Detailed Process:**

1. **Router Agent Invocation:**
   - Sends question to Router Agent
   - Router LLM analyzes question intent
   - No retrieval at this stage (pure classification)

2. **Classification Logic:**
   - **NEEDLE Route:**
     - Single, specific fact needed
     - Examples: "What's the phone?", "When was the accident?"
     - Also: Date calculations ("How many days...?")
   
   - **SUMMARY Route:**
     - Multiple facts or explanation needed
     - Examples: "Summarize the claim", "What happened?"

3. **Output:**
   - route: "needle" or "summary"
   - confidence: 0.0 to 1.0
   - reason: Explanation of decision

**Example:**
```
Question: "What is Jon Mor's phone number?"
Route Decision:
  route: "needle"
  confidence: 0.95
  reason: "Question asks for single specific fact (phone number)"
```

**Why Important:** Different questions need different retrieval strategies. Routing ensures optimal retrieval for each question type.

---

### **Stage 2.6a: Needle Agent Execution (If Routed to NEEDLE)**

**Location:** `orchestrator.py` → Needle Agent

**What it does:**
Retrieves precise chunks and extracts atomic facts.

**Detailed Process:**

1. **Retrieval:**
   - Uses Needle Retriever (top_k=3, threshold=0.75)
   - Embeds user question using OpenAI embedding
   - Performs cosine similarity search in FAISS
   - Returns 3 most similar chunks (if above threshold)
   - Each chunk is ~200 characters (child chunks)

2. **Context Preparation:**
   - Formats retrieved chunks for LLM
   - Includes chunk text + metadata
   - Adds claim context (claim_id, claimant_name)

3. **LLM Invocation (Standard Path):**
   - Sends question + chunks to Needle Agent LLM
   - System prompt: "Extract exact answer from chunks"
   - LLM reads chunks and extracts fact
   - Returns structured response (Pydantic model)

4. **MCP Tool Path (If Date Calculation Needed):**
   - LLM recognizes date calculation in question
   - Extracts dates from retrieved chunks
   - **Tool Call Decision:**
     - LLM with `tool_choice="auto"`
     - LLM decides: "I see two dates, I should call calculate_days_between"
   - **Tool Execution:**
     - Calls: `calculate_days_between("2024-01-24", "2024-02-18")`
     - Tool performs exact calculation using Python datetime
     - Returns: `{"success": True, "number_of_days": 25}`
   - **Final Answer Formation:**
     - LLM receives tool result
     - Formats natural language answer
     - Example: "25 days passed between the accident and repair appointment."

5. **Response Formation:**
   - answer: Extracted fact or "null" if not found
   - confidence: 1.0 if found, 0.0 if not
   - sources: List of chunk IDs used
   - reason: Explanation (may mention MCP tool usage)

**Example (Standard):**
```
Question: "What is Jon Mor's phone?"
Retrieved Chunks:
  1. "Name: Jon Mor, Phone: 555-1234"
  2. "Contact: Jon Mor, 555-1234"
  3. "Address: 123 Main St"

LLM Analysis: "Phone number is 555-1234, found in chunks 1 and 2"

Response:
  answer: "555-1234"
  confidence: 1.0
  sources: ["chunk_abc123", "chunk_def456"]
  reason: "Found exact phone number in contact section"
```

**Example (MCP Tool):**
```
Question: "How many days from accident to repair?"
Retrieved Chunks:
  1. "Accident Date: 2024-01-24"
  2. "Repair Appointment: 2024-02-18"
  3. "Claim filed on 2024-01-26"

LLM Analysis: 
  "I see two dates: 2024-01-24 and 2024-02-18"
  "I need to calculate days between them"
  "I should call the MCP tool"

Tool Call:
  calculate_days_between("2024-01-24", "2024-02-18")
  → Returns: 25 days

Response:
  answer: "25 days"
  confidence: 1.0
  sources: ["chunk_xyz789", "chunk_abc123"]
  reason: "Used MCP date_calculator tool: calculate_days_between(2024-01-24, 2024-02-18) = 25 days"
```

**Why Needle Agent:** For atomic questions, you need high precision. Small chunks + high threshold + fact extraction = accurate answers without hallucination.

---

### **Stage 2.6b: Summary Agent Execution (If Routed to SUMMARY)**

**Location:** `orchestrator.py` → Summary Agent

**What it does:**
Retrieves comprehensive context and synthesizes detailed answers.

**Detailed Process:**

1. **MapReduce Query Engine Approach (Preferred):**
   
   a. **Retrieval Phase:**
      - Uses MapReduce Query Engine
      - Retrieves top_k=15 chunks (more comprehensive)
      - Uses both parent and child chunks
      - No similarity threshold (high recall)
   
   b. **Map Phase:**
      - For each retrieved chunk:
        - LLM generates summary of that chunk
        - Focuses on question-relevant information
      - Results in 15 mini-summaries
   
   c. **Reduce Phase:**
      - LLM combines all mini-summaries
      - Synthesizes coherent final answer
      - Resolves any contradictions
      - Organizes information logically
   
   d. **Final Answer Formation:**
      - Comprehensive response covering all relevant aspects
      - May call MCP tool if date calculations involved

2. **MCP Tool Integration (If Needed):**
   - During synthesis, LLM may recognize need for date calculation
   - Calls calculate_days_between with dates from context
   - Incorporates exact calculation in final answer

3. **Response Formation:**
   - answer: Comprehensive synthesized response
   - confidence: 0.8-0.9 typically (synthesis less certain than extraction)
   - sources: All chunk IDs used (may be 15+)
   - reason: Explanation of synthesis process

**Example:**
```
Question: "Summarize Jon Mor's claim"

Retrieved Chunks (15 chunks covering):
  • Claimant info
  • Incident details
  • Vehicle damage
  • Repair information
  • Claim status
  • Payment details

Map Phase (15 mini-summaries):
  1. "Jon Mor, phone 555-1234..."
  2. "Accident on 2024-01-24 at Main St..."
  3. "Vehicle front bumper damaged..."
  ...

Reduce Phase:
  Combines all summaries into coherent narrative

Response:
  answer: "Jon Mor filed an insurance claim on January 26, 2024, 
           following a vehicle accident on January 24, 2024 at Main 
           Street. The accident resulted in front bumper damage to 
           his vehicle. The repair appointment was scheduled for 
           February 18, 2024 (25 days after the accident). The claim 
           amount is $5,000 and the status is approved. The payment 
           was issued on February 25, 2024."
  confidence: 0.9
  sources: [15+ chunk IDs]
  reason: "Synthesized comprehensive summary from incident, repair, 
           and payment sections. Used MCP tool for date calculation."
```

**Why Summary Agent:** Complex questions need broad context. MapReduce ensures comprehensive coverage while maintaining coherence. LLM synthesis creates natural, flowing answers.

---

### **Stage 2.7: Response Normalization**

**Location:** `orchestrator.py` → `run()` method

**What it does:**
Formats the agent's response into a standardized structure for external consumers.

**Detailed Process:**

1. **Unified Response Creation:**
   - Combines routing metadata + agent result
   - Adds route information (which agent was used)
   - Ensures consistent format regardless of agent

2. **Response Structure:**
   ```python
   {
       "route": "needle" or "summary",
       "answer": "555-1234",
       "confidence": 1.0,
       "sources": ["chunk_abc123", "chunk_def456"],
       "retrieved_chunks_content": ["Phone: 555-1234", ...],
       "reason": "Found in contact section"
   }
   ```

3. **Logging:**
   - Prints route decision
   - Prints final answer
   - Prints confidence score
   - Prints number of sources
   - Prints reasoning

**Why Important:** External systems (GUI, API, evaluation) need consistent interface. Normalization ensures predictable response structure.

---

### **Flow 2 Summary:**

```
User Question: "What is Jon Mor's phone?"
    ↓
[Load Index] (2 seconds)
    → production_index/ loaded into memory
    ↓
[Initialize Agents]
    → Router, Needle, Summary agents ready
    ↓
[Orchestrator]
    ↓
[Query Preprocessing]
    → Detects: claimant_name = "Jon Mor"
    → Creates filtered retriever
    ↓
[Router Agent]
    → Classifies: route = "needle"
    ↓
[Needle Agent]
    → Retrieves 3 chunks (from Jon Mor's claim only)
    → Extracts: "555-1234"
    ↓
[Response Normalization]
    → Formats response
    ↓
Final Answer: "555-1234"
(Total time: ~2-3 seconds)
```

---

## **MCP Tools in the Flow**

### **What are MCP Tools?**

MCP (Model Context Protocol) Tools are **external deterministic functions** that extend LLM capabilities for precise computations that LLMs are bad at (like date arithmetic).

### **Available Tool: Date Calculator**

**Location:** `mcp_tools/date_calculator.py`

**Purpose:** Calculate exact number of days between two dates.

**Why Needed:**
- LLMs are bad at arithmetic (might say "approximately 25 days")
- LLMs can't reliably handle leap years
- Need exact, deterministic results
- No approximation or hallucination

### **How MCP Tools Work in Query Flow:**

```
User Query with Date Calculation:
"How many days from accident to repair?"
    ↓
[Router Agent]
    → Classifies as NEEDLE (date calculation detected)
    ↓
[Needle Agent]
    → Retrieves chunks:
       • "Accident: 2024-01-24"
       • "Repair: 2024-02-18"
    ↓
[LLM Analysis]
    → Recognizes: "I see two dates, I need exact calculation"
    → Decision: Call MCP tool
    ↓
[MCP Tool Invocation]
    → Function: calculate_days_between("2024-01-24", "2024-02-18")
    → Python datetime computation
    → Returns: {"success": True, "number_of_days": 25}
    ↓
[LLM Response Formation]
    → Receives: 25 days (exact)
    → Formats: "25 days passed between accident and repair"
    ↓
Final Answer: "25 days" (deterministic, guaranteed correct)
```

### **Key Principles:**

1. **LLMs Orchestrate, Tools Compute:**
   - LLM understands question intent
   - LLM extracts dates from context
   - Tool performs exact calculation
   - LLM formats final answer

2. **Deterministic Computation:**
   - Same dates → Same result, always
   - No approximation, no hallucination
   - Handles leap years, month boundaries

3. **Transparent Usage:**
   - Agent's "reason" field mentions tool usage
   - Example: "Used MCP date_calculator tool: ..."
   - Enables auditing and debugging

4. **Automatic Decision:**
   - LLM decides WHEN to use tool (tool_choice="auto")
   - No hardcoded rules in Python
   - LLM recognizes date calculation patterns

---

## **Evaluation Systems**

The project includes **two independent evaluation frameworks** to assess RAG system performance.

---

### **Evaluation 1: LLM-as-a-Judge (Primary)**

**Location:** `evaluation/`

**Purpose:** Custom evaluation framework tailored to insurance claim domain.

**Components:**

1. **Test Cases:**
   - File: `test_cases.json`
   - 8 test questions covering:
     - Atomic facts (phone, dates, amounts)
     - Complex questions (summaries, timelines)
     - Edge cases (unanswerable questions)
   - Each test case has:
     - question
     - ground_truth (expected answer)
     - expected_chunks (specific chunks that should be retrieved)

2. **Judge LLM:**
   - Model: Google Gemini 2.5-flash
   - Why different from RAG system (gpt-4o-mini):
     - Prevents bias (judge ≠ answerer)
     - Independent evaluation
     - Catches issues the answering LLM might miss

3. **Evaluation Metrics (3):**

   **a. Answer Correctness:**
   - Question: Does system's answer match ground truth?
   - Process:
     - Judge LLM compares system answer vs. ground truth
     - Semantic comparison (not exact string match)
     - Returns: 0.0 (wrong) to 1.0 (perfect)
   - Example:
     - Ground truth: "555-1234"
     - System answer: "The phone number is 555-1234"
     - Score: 1.0 (semantically equivalent)

   **b. Context Relevancy:**
   - Question: Are retrieved chunks relevant to question?
   - Process:
     - Judge LLM examines each retrieved chunk
     - Determines if chunk helps answer question
     - Calculates: (relevant chunks) / (total chunks)
   - Example:
     - Question: "What's the claim amount?"
     - Chunks: "Amount: $5,000" ✅, "Phone: 555-1234" ❌
     - Score: 0.5 (1 relevant, 1 irrelevant)

   **c. Context Recall (Expected Chunks):**
   - Question: Did we retrieve the expected chunks?
   - Process:
     - Test case specifies which chunks SHOULD be retrieved
     - Judge checks if expected chunks are in retrieved set
     - Calculates: (retrieved expected) / (total expected)
   - Example:
     - Expected chunks: ["chunk_123", "chunk_456"]
     - Retrieved chunks: ["chunk_123", "chunk_789"]
     - Score: 0.5 (found 1 of 2 expected)

4. **Evaluation Process:**
   - Run: `python evaluation/run_evaluation.py`
   - For each test case:
     - Query RAG system
     - Collect answer and retrieved chunks
     - Judge LLM evaluates all 3 metrics
     - Save scores
   - Output: `evaluation_results.json`

5. **Why Custom Evaluation:**
   - Domain-specific (knows insurance claims)
   - Expected chunks validation (structural check)
   - Tailored to project needs
   - Can add custom metrics easily

---

### **Evaluation 2: RAGAS (Secondary)**

**Location:** `evaluation-ragas/`

**Purpose:** Industry-standard RAG evaluation using established framework.

**Components:**

1. **Test Cases:**
   - Uses same `test_cases.json` from custom evaluation
   - Ensures consistency across evaluations

2. **Evaluator LLM:**
   - Model: OpenAI gpt-4o-mini
   - Why different from custom judge (Gemini):
     - Cross-validation with different LLM
     - More stable than Gemini experimental models
     - Fast and cost-effective

3. **RAGAS Metrics (4):**

   **a. Context Recall:**
   - Question: Can ground truth be attributed to retrieved contexts?
   - Process:
     - LLM checks if ground truth information exists in chunks
     - Different from custom "expected chunks" metric
     - Focuses on information content, not specific chunks
   - Example:
     - Ground truth: "555-1234"
     - Chunks: "Phone: 555-1234" ✅
     - Score: 1.0

   **b. Context Precision:**
   - Question: Are relevant contexts ranked higher than irrelevant?
   - Process:
     - LLM evaluates each chunk for relevance
     - Calculates precision at each position
     - Higher scores = relevant chunks appear first
   - Example:
     - Position 1: Relevant ✅
     - Position 2: Relevant ✅
     - Position 3: Irrelevant ❌
     - Score: 0.89 (weighted precision)

   **c. Faithfulness:**
   - Question: Is answer grounded in context? (No hallucination?)
   - Process:
     - LLM breaks answer into claims
     - For each claim, checks if supported by chunks
     - Calculates: (supported claims) / (total claims)
   - Example:
     - Answer: "Accident on Jan 24, driver was speeding"
     - Chunks: Only "Accident: Jan 24" ✅, no speeding info ❌
     - Score: 0.5 (1 supported, 1 hallucinated)

   **d. Answer Relevancy:**
   - Question: Does answer address the user's question?
   - Process:
     - LLM generates questions from the answer
     - Compares generated questions to original
     - High similarity = answer is relevant
   - Example:
     - Original Q: "What's the phone?"
     - Generated Q: "What is the phone number?" ✅
     - Score: 0.95 (highly similar)

4. **Evaluation Process:**
   - Run: `python evaluation-ragas/ragas_eval.py`
   - For each test case:
     - Query RAG system
     - Collect answer and contexts
     - Build RAGAS dataset
     - RAGAS library evaluates all 4 metrics
     - Save scores
   - Output: `ragas_results.json`

5. **Visualization:**
   - Run: `python evaluation-ragas/visualize_results.py`
   - Generates: `ragas_visualization.png`
   - Charts:
     - Overall metric scores (bar chart)
     - Context precision by question
     - Answer relevancy by question
     - Heatmap of all metrics

6. **Why RAGAS:**
   - Industry-standard (comparable to other RAG systems)
   - Framework-agnostic (works with any RAG)
   - Comprehensive (4 metrics covering different aspects)
   - Well-maintained library

---

### **Evaluation Comparison:**

```
┌─────────────────────────────────────────────────────────┐
│       CUSTOM LLM-AS-A-JUDGE vs. RAGAS                   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  CUSTOM (evaluation/):                                  │
│  • Judge: Gemini 2.5-flash                              │
│  • Metrics: 3 (Answer, Context Relevancy, Expected)     │
│  • Focus: Domain-specific, structural validation        │
│  • Strength: Tailored to insurance claims               │
│                                                         │
│  RAGAS (evaluation-ragas/):                             │
│  • Judge: OpenAI gpt-4o-mini                            │
│  • Metrics: 4 (Recall, Precision, Faithfulness, Relevancy)│
│  • Focus: General RAG quality, standard framework       │
│  • Strength: Industry benchmarking, cross-validation    │
│                                                         │
│  WHY BOTH:                                              │
│  ✅ Cross-validation (different LLMs, different angles) │
│  ✅ Comprehensive coverage (7 total metrics)            │
│  ✅ Domain + General perspectives                       │
│  ✅ Increased confidence in results                     │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

### **Running Evaluations:**

**Via Command Line:**
```bash
# Custom LLM-as-a-Judge
python evaluation/run_evaluation.py

# RAGAS
python evaluation-ragas/ragas_eval.py
python evaluation-ragas/visualize_results.py
```

**Via GUI:**
```bash
streamlit run app/gui_app.py

# In GUI:
# 1. Click "Run Custom Evaluation" button
# 2. Click "Run RAGAS Evaluation" button
# 3. Click "Compare Evaluations" to see side-by-side
```

---

### **Evaluation Results Interpretation:**

**Score Thresholds:**
- 🟢 **Excellent (0.9-1.0):** System performing very well
- 🟡 **Good (0.7-0.9):** Room for improvement, but functional
- 🟠 **Moderate (0.5-0.7):** Significant issues, needs attention
- 🔴 **Poor (0.0-0.5):** Critical problems, requires fixes

**Example Results:**
```
Custom LLM-as-a-Judge:
  Answer Correctness:      0.95 🟢
  Context Relevancy:       0.88 🟡
  Context Recall:          0.92 🟢

RAGAS:
  Context Recall:          0.95 🟢
  Context Precision:       0.87 🟡
  Faithfulness:            0.99 🟢
  Answer Relevancy:        0.92 🟢

Analysis:
  ✅ Excellent answer quality (correctness, relevancy, faithfulness)
  ✅ Good retrieval (high recall)
  ⚠️  Context precision could improve (some irrelevant chunks)
  
Recommendation:
  Increase similarity_threshold from 0.75 to 0.80 to improve precision
```

---

# 📝 **Short Version**

## **What is RagAgentv2?**

A production RAG system for insurance claim processing. Users ask questions about claim documents, system provides accurate, grounded answers.

---

## **Two Main Flows:**

### **Flow 1: Build Index (Once)**

**Purpose:** Transform PDF → Searchable Index

**Steps:**
1. **PDF Ingestion:** PDF → Clean text
2. **Claim Segmentation:** 1 PDF → 20 claims
3. **Chunking:** Claims → 550 hierarchical chunks
4. **Indexing:** Chunks → Embedded vectors + FAISS

**Output:** `production_index/` folder

**Duration:** ~5-10 minutes

---

### **Flow 2: Answer Questions (Every Query)**

**Purpose:** Use index to answer questions fast

**Steps:**
1. **Load Index:** Load production_index/ (~2 sec)
2. **Initialize Agents:** Router, Needle, Summary
3. **Preprocess:** Detect claim-specific queries
4. **Route:** Router classifies question (needle/summary)
5. **Execute:** 
   - Needle Agent: Extract atomic facts (3 chunks, high precision)
   - Summary Agent: Synthesize comprehensive answers (15+ chunks, MapReduce)
   - MCP Tools: Call date calculator if needed (deterministic computation)
6. **Return:** Natural language answer

**Duration:** 2-5 seconds

---

## **MCP Tools:**

**What:** External functions for precise computation

**When:** Date calculations (e.g., "How many days from accident to repair?")

**How:** 
- LLM recognizes need for calculation
- Calls `calculate_days_between(start, end)`
- Tool returns exact days (no hallucination)
- LLM formats answer

---

## **Evaluation (Two Systems):**

### **1. Custom LLM-as-a-Judge:**
- Judge: Gemini 2.5-flash
- Metrics: Answer Correctness, Context Relevancy, Context Recall
- Focus: Insurance claims domain

### **2. RAGAS:**
- Judge: OpenAI gpt-4o-mini
- Metrics: Context Recall, Context Precision, Faithfulness, Answer Relevancy
- Focus: Industry-standard RAG evaluation

**Why Both:** Cross-validation, comprehensive coverage, different perspectives

---

# 🎯 **Overall Project Summary**

## **Project Goal:**

Build a production-ready RAG system that enables natural language querying of insurance claim documents with high accuracy, no hallucination, and fast response times.

---

## **Key Features:**

1. **Multi-Claim Processing:**
   - Handles PDFs with 20+ claims
   - Claim-level isolation prevents cross-contamination

2. **Hierarchical Chunking:**
   - 3-level structure (sections, parents, children)
   - Optimized for different question types

3. **Intelligent Routing:**
   - Automatic classification (needle vs. summary)
   - Different strategies for different questions

4. **MCP Tool Integration:**
   - Deterministic date calculations
   - No approximation or hallucination
   - Transparent tool usage

5. **Dual Evaluation:**
   - Custom + RAGAS frameworks
   - Comprehensive quality assessment
   - Cross-validation

6. **Production-Ready:**
   - Two-phase architecture (build once, query many)
   - Fast response times (2-5 seconds)
   - Scalable (handles concurrent users)

---

## **Technology Stack:**

- **RAG Framework:** LlamaIndex
- **LLM Orchestration:** LangChain
- **Vector Database:** FAISS
- **Embeddings:** OpenAI text-embedding-3-small
- **LLMs:** OpenAI gpt-4o-mini (RAG), Gemini 2.5-flash (evaluation)
- **PDF Processing:** pypdf
- **Evaluation:** Custom + RAGAS
- **GUI:** Streamlit

---

## **System Components:**

```
┌─────────────────────────────────────────────────────────┐
│              SYSTEM ARCHITECTURE                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  BUILD TIME (Flow 1):                                   │
│  PDF Ingestion → Claim Segmentation → Chunking → Index │
│                                                         │
│  QUERY TIME (Flow 2):                                   │
│  Load Index → Agents → Orchestrator → Route → Answer   │
│                                                         │
│  AGENTS:                                                │
│  Router (classify) → Needle (extract) → Summary (synthesize)│
│                                                         │
│  EXTENSIONS:                                            │
│  MCP Tools (date calculations)                          │
│                                                         │
│  EVALUATION:                                            │
│  Custom LLM-as-a-Judge + RAGAS (7 total metrics)        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## **Success Metrics:**

Based on current evaluation results:
- ✅ Answer Correctness: 0.95 (Excellent)
- ✅ Faithfulness: 0.99 (No hallucination)
- ✅ Context Recall: 0.95 (Retrieving right information)
- 🟡 Context Precision: 0.87 (Good, room for optimization)

---

## **Use Cases:**

1. **Atomic Queries:** "What is Jon Mor's phone number?" → "555-1234"
2. **Complex Queries:** "Summarize the claim" → Comprehensive timeline
3. **Date Calculations:** "Days from accident to repair?" → "25 days" (MCP tool)
4. **Claim-Specific:** "Jon Mor's phone?" → Only Jon's data (no cross-contamination)
5. **Unanswerable:** "What's the color?" → "null" (honest, no guessing)

---

## **Key Design Principles:**

1. **Separation of Concerns:** Each layer has one job
2. **Build Once, Query Many:** Efficiency through pre-computation
3. **No Hallucination:** Strict grounding, MCP tools for computation
4. **Claim Isolation:** Independent processing per claim
5. **Hierarchical Retrieval:** Different granularity for different questions
6. **Deterministic Tools:** LLMs orchestrate, tools compute
7. **Dual Evaluation:** Multiple perspectives for comprehensive assessment

---

## **Project Structure:**

```
RagAgentv2/
├── RAG/
│   ├── PDF_Ingestion/          (Stage 1.1: PDF → Clean text)
│   ├── Claim_Segmentation/     (Stage 1.2: Split claims)
│   ├── Chunking_Layer/         (Stage 1.3: Create hierarchy)
│   ├── Index_Layer/            (Stage 1.4: Embed + FAISS)
│   ├── Agents/                 (Router, Needle, Summary)
│   └── Orchestration/          (Coordinator)
│
├── mcp_tools/                  (Date calculator tool)
│
├── evaluation/                 (Custom LLM-as-a-Judge)
├── evaluation-ragas/           (RAGAS evaluation)
│
├── app/                        (Streamlit GUI)
│
├── build_production_index.py   (Flow 1: Build index)
├── main.py                     (Flow 2: Query system)
│
└── production_index/           (Pre-built index)
```

---

## **Quick Start:**

```bash
# 1. Build index (once)
python build_production_index.py

# 2. Query system (interactive)
python main.py

# 3. Or use GUI
streamlit run app/gui_app.py

# 4. Run evaluations
python evaluation/run_evaluation.py
python evaluation-ragas/ragas_eval.py
```

---

## **Future Enhancements:**

- Add more MCP tools (currency conversion, unit conversion)
- Support for more document types (emails, forms)
- Real-time index updates (incremental indexing)
- Multi-document queries across claims
- Advanced analytics dashboard
- API deployment for external systems

---

**Built for production-grade insurance claim processing with accuracy, speed, and reliability.** 🚗📄🤖

---

## **Documentation Map:**

For deeper understanding of each component, see:

- `RAG/PDF_Ingestion/pdf-ingestion-explained.md`
- `RAG/Claim_Segmentation/claim-segmentation-explained.md`
- `RAG/Chunking_Layer/chunking-layer-explained.md`
- `RAG/Index_Layer/index-layer-explained.md`
- `RAG/Agents/agents-explained.md`
- `RAG/Orchestration/orchestrator-explained.md`
- `mcp_tools/mcp-tools-explained.md`
- `evaluation/evaluation_explained.md`
- `evaluation-ragas/evaluation-ragas-explained.md`
- `RAG_SYSTEM_FLOW.md`

**This document (PROJECT_OVERVIEW.md) provides the complete picture of how everything fits together.** 🎯
