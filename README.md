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

## Usage

### Layer 1: PDF Ingestion

```python
from RAG.PDF_Ingestion import create_ingestion_pipeline

# Create pipeline
pipeline = create_ingestion_pipeline(document_type="insurance_claim_form")

# Ingest PDF
document = pipeline.ingest("path/to/file.pdf")

# Access document
print(document.doc_id)
print(document.metadata)
print(document.text[:500])
```

### Layer 2: Chunking

```python
from RAG.PDF_Ingestion import create_ingestion_pipeline
from RAG.Chunking_Layer import create_chunking_pipeline

# Get document from Layer 1
pipeline = create_ingestion_pipeline(document_type="insurance_claim_form")
document = pipeline.ingest("path/to/file.pdf")

# Create hierarchical nodes
chunking_pipeline = create_chunking_pipeline(
    parent_chunk_size=400,
    child_chunk_size=120
)
nodes = chunking_pipeline.build_nodes(document)

# Access nodes
print(f"Total nodes: {len(nodes)}")
```

### Testing Layers

Run the test notebooks:

```bash
# Layer 1
cd RAG/PDF_Ingestion
jupyter notebook test_pdf_ingestion.ipynb

# Layer 2
cd RAG/Chunking_Layer
jupyter notebook test_chunking_layer.ipynb
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
