# RAG Agent v2 - Production-Grade RAG System

A modular, scalable Retrieval-Augmented Generation (RAG) system designed for production use with **multi-claim document processing** and **smart metadata filtering**.

Advanced RAG system for insurance claims using multi-agent AI architecture. Automatically routes questions to specialized agents, uses auto-merging retrieval for precise answers, handles complex summaries with map-reduce, and performs date calculations with MCP tools. Includes GUI showing retrieval processes and complete evaluation framework.

## 🚀 Quick Start

 Interactive Script
```bash
# Build production index (once)
python build_production_index.py

# Query the system
python main.py
# Then type questions interactively

or GUI experience

# Build production index (once)
python build_production_index.py

# Launch web interface
streamlit run app/gui_app.py
```
you might need enter your email for GUI expirience

evaluation
```bash
#ragas evaluation
python evaluation-ragas/ragas_eval.py

#custom llm as a jusge evaluation (need to enter gemini api key in .env GOOGLE_API_KEY="")
python evaluation/run_evaluation.py 
```

### Supported Query Formats
✅ **By claim number**: "Summarize claim number 5", "What is form #1 about?"  
✅ **By claimant name**: "What is Eli Cohen's phone number?", "Summarize Jon Mor's claim"  
✅ **All 20 claims**: Indexed and searchable simultaneously

---

## Architecture


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
│                   FLOW 1: BUILD INDEX                         │
│                      (Run Once)                          │
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
│  │  STAGE 2.1: LOAD PRODUCTION INDEX (The out put of Flow 1)                              │    │
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

This system is built in **5 strict layers**:

### Layer 1: PDF Ingestion ✅ COMPLETE
- **Input**: PDF file
- **Output**: Clean LlamaIndex Document with metadata
- **Status**: Implemented and tested
- **Location**: `RAG/PDF_Ingestion/`

### Layer 2: Chunking ✅ COMPLETE
- **Input**: LlamaIndex Document
- **Output**: Hierarchical Nodes (Sections → Parent → Child)
- **Status**: Implemented and tested
- **Location**: `RAG/Chunking_Layer/`

### Layer 3: Index
- **Input**: Hierarchical Nodes
- **Output**: VectorStoreIndex + SummaryIndex + AutoMergingRetriever
- **Status**: Not yet implemented

### Layer 4: Agents
- **Input**: Indexes and Retrievers
- **Output**: Router Agent, Needle Agent, Summary Agent
- **Status**: Not yet implemented

### Layer 5: Orchestration
- **Input**: All agents
- **Output**: Complete RAG pipeline
- **Status**: Not yet implemented

## Technology Stack

- **RAG Core**: LlamaIndex (documents, nodes, chunking, indexes, retrieval)
- **Agents & Orchestration**: LangChain (LCEL, Runnables, Chains)
- **Vector Store**: FAISS
- **Embeddings**: OpenAI Embeddings (via LlamaIndex)
- **LLM**: OpenAI GPT models

## Setup

### 1. Create Virtual Environment (conda)

```bash
conda create -n ragagent python=3.11 -y
conda activate ragagent
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

Create a `.env` file in the project root:

```
OPENAI_API_KEY=your_openai_api_key_here
```


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
## Design Principles

### Strict Layer Separation
- Each layer has ONE responsibility
- No cross-layer contamination
- Clear input/output contracts

### Embedding Consistency
- Embeddings defined ONCE during index construction
- Reused implicitly via StorageContext
- Never instantiated at query time

### Production Quality
- Heavy inline documentation explaining WHY
- Comprehensive error handling
- Deterministic behavior
- Extensive testing

### No Shortcuts
- No premature optimization
- No mixing of responsibilities
- No simplifications that break the architecture

## Development

### Adding a New Layer

1. Create folder: `RAG/LayerName/`
2. Create `__init__.py` with exports
3. Create main module: `layer_name.py`
4. Create test notebook: `test_layer_name.ipynb`
5. Document inputs, outputs, and responsibilities
6. Test in isolation before integrating

### Testing

Each layer includes a Jupyter notebook for human inspection:
- Validates layer functionality
- Inspects intermediate outputs
- Provides debugging visibility
- Documents expected behavior

## Current Status

- ✅ **Layer 1 (PDF Ingestion)**: Complete and tested
- ✅ **Layer 2 (Claim Segmentation)**: Complete - handles multi-claim PDFs (20 claims)
- ✅ **Layer 3 (Chunking)**: Complete - hierarchical nodes with claim metadata
- ✅ **Layer 4 (Index)**: Complete - FAISS vector store + SummaryIndex
- ✅ **Layer 5 (Agents)**: Complete - Router, Needle, Summary agents
- ✅ **Layer 6 (Orchestration)**: Complete - Full pipeline with metadata filtering
- ✅ **Production Index**: Fast query system with pre-built indexes
- ✅ **Metadata Filtering**: Smart claim-specific queries (e.g., "claim number 5")

## License

Internal project - Not for distribution
