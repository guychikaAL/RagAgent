# RAG Agent v2 - Production-Grade RAG System

A modular, scalable Retrieval-Augmented Generation (RAG) system designed for production use with **multi-claim document processing** and **smart metadata filtering**.

Advanced RAG system for insurance claims using multi-agent AI architecture. Automatically routes questions to specialized agents, uses auto-merging retrieval for precise answers, handles complex summaries with map-reduce, and performs date calculations with MCP tools. Includes GUI showing retrieval processes and complete evaluation framework.

## 🚀 Quick Start

### Option 1: Simple Notebook (Recommended)
```bash
# Open ask_questions.ipynb
jupyter notebook ask_questions.ipynb

# Run the setup cell, then ask questions like:
# - "What is Jon Mor's phone number?"
# - "Summarize claim number 5"
# - "What happened in Eli Cohen's accident?"
```

### Option 2: Interactive Script
```bash
# Build production index (once)
python build_production_index.py

# Query the system
python main.py
# Then type questions interactively
```

### Supported Query Formats
✅ **By claim number**: "Summarize claim number 5", "What is form #1 about?"  
✅ **By claimant name**: "What is Eli Cohen's phone number?", "Summarize Jon Mor's claim"  
✅ **All 20 claims**: Indexed and searchable simultaneously

---

## Architecture

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

## Project Structure

```
RagAgentv2/
├── .env                          # Environment variables (not in git)
├── .gitignore                    # Git ignore rules
├── requirements.txt              # Python dependencies
├── README.md                     # This file
├── auto_claim_20_forms_FINAL.pdf # Sample PDF
└── RAG/
    ├── __init__.py
    ├── PDF_Ingestion/            # Layer 1: PDF Ingestion ✅
    │   ├── __init__.py
    │   ├── pdf_ingestion.py      # Main ingestion module
    │   └── test_pdf_ingestion.ipynb  # Test notebook
    └── Chunking_Layer/           # Layer 2: Chunking ✅
        ├── __init__.py
        ├── chunking_layer.py     # Main chunking module
        └── test_chunking_layer.ipynb # Test notebook
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
