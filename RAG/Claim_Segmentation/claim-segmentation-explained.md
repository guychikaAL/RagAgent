# Claim Segmentation Layer - Complete Guide

## 📄 **What is the Claim Segmentation Layer?**

The Claim Segmentation Layer **splits one PDF document containing multiple insurance claims into separate documents** (one per claim). Each claim is an independent business entity that needs isolated processing to prevent mixing facts across different claims.

---

## 🎯 **Core Responsibility**

```
┌─────────────────────────────────────────────────────────┐
│          CLAIM SEGMENTATION LAYER                       │
│      (One PDF → Multiple Claim Documents)               │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  INPUT:  One Document (entire PDF)                      │
│          • May contain 20+ claims                       │
│          • Each claim has its own form                  │
│                                                         │
│  OUTPUT: List[Document] (one per claim)                │
│          • Document 1: Claim #001 (Jon Mor)             │
│          • Document 2: Claim #002 (Jane Smith)          │
│          • Document 3: Claim #003 (Bob Johnson)         │
│          • ...                                          │
│                                                         │
│  DOES:                                                  │
│  ✅ Detect claim boundaries                             │
│  ✅ Split PDF into separate claims                      │
│  ✅ Extract claim-specific metadata                     │
│  ✅ Extract claimant names dynamically                  │
│                                                         │
│  DOES NOT:                                              │
│  ❌ Chunk text (Chunking Layer's job)                   │
│  ❌ Create nodes (Chunking Layer's job)                 │
│  ❌ Create embeddings (Index Layer's job)               │
│  ❌ Perform retrieval (Index Layer's job)               │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 🏗️ **Why This Layer Exists**

### **The Problem:**

```
WITHOUT Claim Segmentation:
─────────────────────────────────────────
PDF contains:
  • Claim #1: Jon Mor, accident on 2024-06-06
  • Claim #2: Jane Smith, accident on 2024-05-15
  • Claim #3: Bob Johnson, accident on 2024-07-01

User Query: "When did Jon Mor's accident occur?"

RAG System retrieves:
  ✅ Chunk: "Jon Mor, phone: 555-1234"
  ❌ Chunk: "Accident: 2024-05-15" (from Jane's claim!)
  ❌ Chunk: "Incident date: 2024-07-01" (from Bob's claim!)

Answer: "2024-05-15" ❌ WRONG! (Mixed up claims)
```

---

### **The Solution:**

```
WITH Claim Segmentation:
─────────────────────────────────────────
PDF segmented into:
  → Claim Doc #1: Jon Mor only
  → Claim Doc #2: Jane Smith only
  → Claim Doc #3: Bob Johnson only

Each claim indexed separately:
  → Index 1: Jon Mor's chunks (claim_id: "001")
  → Index 2: Jane's chunks (claim_id: "002")
  → Index 3: Bob's chunks (claim_id: "003")

User Query: "When did Jon Mor's accident occur?"

RAG System:
  1. Filters: claim_id="001" (Jon Mor only)
  2. Retrieves: Chunks from Jon's claim only
  3. Answer: "2024-06-06" ✅ CORRECT!

Result: No mixing! Each claim isolated!
```

---

## 📍 **Where It Fits in the Pipeline**

```
┌─────────────────────────────────────────────────────────┐
│              COMPLETE RAG PIPELINE                      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1. PDF INGESTION                                       │
│     PDF File → Single Document                          │
│     ↓                                                    │
│                                                         │
│  2. CLAIM SEGMENTATION ← YOU ARE HERE                   │
│     Single Document → List[Documents] (one per claim)   │
│     ↓                                                    │
│                                                         │
│  3. CHUNKING (per claim)                                │
│     Each Claim Document → Hierarchical Nodes            │
│     ↓                                                    │
│                                                         │
│  4. INDEX (per claim or all claims)                     │
│     Nodes → Embeddings → Vector Store                   │
│     ↓                                                    │
│                                                         │
│  5. ORCHESTRATOR (query time)                           │
│     Router → Agent → Retriever → Answer                 │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

### **Why Before Chunking?**

```
CORRECT ORDER:
─────────────────────────────────────────
1. Segment PDF into claims
2. Chunk each claim separately
3. Index each claim with claim_id metadata

WHY:
✅ Chunking operates on single-claim text
✅ Each claim gets its own hierarchical structure
✅ Metadata includes claim_id for filtering
✅ No cross-claim contamination


WRONG ORDER (if we chunked first):
─────────────────────────────────────────
1. Chunk entire PDF (mixed claims)
2. Try to figure out which chunk belongs to which claim

PROBLEMS:
❌ Chunks at claim boundaries would mix claims
❌ No way to filter by claim_id later
❌ Metadata extraction becomes impossible
❌ Parent-child relationships span multiple claims
```

---

## 🔄 **Claim Segmentation Process**

### **Overview:**

```
┌──────────────────────────────────────────────────────────┐
│        CLAIM SEGMENTATION PIPELINE (2 STAGES)            │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Input: Single Document (entire PDF)                    │
│     ↓                                                     │
│  ┌────────────────────────────────────────────────┐     │
│  │ STAGE 1: Detect Claim Boundaries               │     │
│  │ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │     │
│  │ • Scan document for claim markers              │     │
│  │ • "AUTO CLAIM FORM #N" patterns                │     │
│  │ • "Claim Number:" patterns                     │     │
│  │ • Record position of each boundary             │     │
│  │                                                │     │
│  │ Result: List[ClaimBoundary]                    │     │
│  │   [Boundary(#1, pos=0),                        │     │
│  │    Boundary(#2, pos=1500),                     │     │
│  │    Boundary(#3, pos=3000), ...]                │     │
│  └────────────────────────────────────────────────┘     │
│     ↓                                                     │
│  ┌────────────────────────────────────────────────┐     │
│  │ STAGE 2: Create Claim Documents                │     │
│  │ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │     │
│  │ For each boundary:                             │     │
│  │   1. Extract text slice                        │     │
│  │   2. Extract claimant name (dynamic!)          │     │
│  │   3. Generate claim_id                         │     │
│  │   4. Create Document with metadata             │     │
│  │                                                │     │
│  │ Result: List[Document]                         │     │
│  │   [Doc(claim_id="001", claimant="Jon Mor"),    │     │
│  │    Doc(claim_id="002", claimant="Jane Smith"), │     │
│  │    Doc(claim_id="003", claimant="Bob Johnson")]│     │
│  └────────────────────────────────────────────────┘     │
│     ↓                                                     │
│  Output: 20 Claim Documents                             │
│          (ready for Chunking Layer)                      │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## 🔍 **Stage 1: Detect Claim Boundaries**

### **Purpose:**
Identify where each claim starts in the PDF text.

### **Detection Strategy:**

```
┌──────────────────────────────────────────────────────────┐
│           CLAIM BOUNDARY DETECTION                       │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  PATTERN 1: "AUTO CLAIM FORM #N" (Primary)              │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│  Regex: AUTO\s+CLAIM\s+FORM\s+#(\d+)                    │
│                                                          │
│  Matches:                                               │
│  ✓ "AUTO CLAIM FORM #1"                                  │
│  ✓ "AUTO CLAIM FORM #20"                                 │
│  ✓ "Auto Claim Form #5" (case-insensitive)              │
│                                                          │
│  Example in PDF:                                        │
│  ┌────────────────────────────────────────┐             │
│  │ AUTO CLAIM FORM #1                     │ ← Boundary 1│
│  │ Name: Jon Mor                          │             │
│  │ Phone: 555-1234                        │             │
│  │ ...                                    │             │
│  │                                        │             │
│  │ AUTO CLAIM FORM #2                     │ ← Boundary 2│
│  │ Name: Jane Smith                       │             │
│  │ Phone: 555-5678                        │             │
│  │ ...                                    │             │
│  └────────────────────────────────────────┘             │
│                                                          │
│  PATTERN 2: "Claim Number:" (Fallback)                  │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│  Regex: Claim\s+Number:\s*([A-Z0-9]+)                   │
│                                                          │
│  Used if Pattern 1 finds nothing.                       │
│  Matches field values instead of headers.               │
│                                                          │
│  PATTERN 3: Section Headers (Last Resort)               │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│  Regex: ^SECTION\s+1\s*[–-]\s*CLAIMANT\s+INFORMATION    │
│                                                          │
│  Used if no other patterns found.                       │
│  Assumes document starts with structured sections.      │
│                                                          │
│  FALLBACK: No Boundaries Detected                       │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│  If all patterns fail:                                  │
│  → Treat entire PDF as ONE claim                        │
│  → Return List with 1 document                          │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

### **Boundary Detection Flow:**

```
┌──────────────────────────────────────────────────────────┐
│                                                          │
│  Input: Full PDF Text                                   │
│     ↓                                                     │
│  ┌────────────────────────────────────────────────┐     │
│  │ Try Pattern 1: "AUTO CLAIM FORM #N"            │     │
│  │ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │     │
│  │ for match in re.finditer(pattern1, text):      │     │
│  │   claim_number = match.group(1)                │     │
│  │   start_pos = match.start()                    │     │
│  │   boundaries.append(...)                       │     │
│  └────────────────────────────────────────────────┘     │
│     ↓                                                     │
│  Found boundaries? YES → Skip to sorting                │
│     ↓ NO                                                 │
│  ┌────────────────────────────────────────────────┐     │
│  │ Try Pattern 2: "Claim Number:"                 │     │
│  │ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │     │
│  │ for match in re.finditer(pattern2, text):      │     │
│  │   ...                                          │     │
│  └────────────────────────────────────────────────┘     │
│     ↓                                                     │
│  Found boundaries? YES → Skip to sorting                │
│     ↓ NO                                                 │
│  ┌────────────────────────────────────────────────┐     │
│  │ Try Pattern 3: Section headers                │     │
│  │ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │     │
│  │ if re.search(pattern3, text):                  │     │
│  │   boundaries.append(ClaimBoundary(...))        │     │
│  └────────────────────────────────────────────────┘     │
│     ↓                                                     │
│  ┌────────────────────────────────────────────────┐     │
│  │ Sort Boundaries by Position                    │     │
│  │ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │     │
│  │ boundaries.sort(key=lambda b: b.start_char)    │     │
│  └────────────────────────────────────────────────┘     │
│     ↓                                                     │
│  ┌────────────────────────────────────────────────┐     │
│  │ Remove Duplicates                              │     │
│  │ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │     │
│  │ Keep boundaries > 50 chars apart              │     │
│  │ WHY: Multiple patterns may match same claim    │     │
│  └────────────────────────────────────────────────┘     │
│     ↓                                                     │
│  Output: List[ClaimBoundary]                            │
│          Sorted, deduplicated                            │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

### **Example: Detecting Boundaries**

```
Input PDF Text:
─────────────────────────────────────────
"This is a test PDF.

AUTO CLAIM FORM #1
Name: Jon Mor
Phone: 555-1234
...

AUTO CLAIM FORM #2
Name: Jane Smith
Phone: 555-5678
...

AUTO CLAIM FORM #3
Name: Bob Johnson
Phone: 555-9012
..."
─────────────────────────────────────────

Detected Boundaries:
─────────────────────────────────────────
ClaimBoundary(
  claim_number="1",
  start_char=23,
  title="AUTO CLAIM FORM #1"
)

ClaimBoundary(
  claim_number="2",
  start_char=98,
  title="AUTO CLAIM FORM #2"
)

ClaimBoundary(
  claim_number="3",
  start_char=185,
  title="AUTO CLAIM FORM #3"
)
─────────────────────────────────────────
```

---

## 📄 **Stage 2: Create Claim Documents**

### **Purpose:**
Convert boundaries into separate Document objects with claim-specific metadata.

### **Flow:**

```
┌──────────────────────────────────────────────────────────┐
│          CREATE CLAIM DOCUMENTS                          │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Input: Original Document + List[ClaimBoundary]         │
│     ↓                                                     │
│  For each boundary (i):                                 │
│     ↓                                                     │
│  ┌────────────────────────────────────────────────┐     │
│  │ STEP 1: Extract Text Slice                     │     │
│  │ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │     │
│  │ start_pos = boundary[i].start_char             │     │
│  │ end_pos = boundary[i+1].start_char             │     │
│  │           (or end of document)                 │     │
│  │                                                │     │
│  │ claim_text = text[start_pos:end_pos]           │     │
│  └────────────────────────────────────────────────┘     │
│     ↓                                                     │
│  ┌────────────────────────────────────────────────┐     │
│  │ STEP 2: Generate claim_id (deterministic)      │     │
│  │ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │     │
│  │ claim_id_string = f"{doc_id}_claim_{i}"        │     │
│  │ claim_id = sha256(claim_id_string)[:16]        │     │
│  │                                                │     │
│  │ WHY: Same claim always gets same ID            │     │
│  └────────────────────────────────────────────────┘     │
│     ↓                                                     │
│  ┌────────────────────────────────────────────────┐     │
│  │ STEP 3: Extract Claimant Name (DYNAMIC!)       │     │
│  │ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │     │
│  │ Look for: "Name: FirstName LastName"           │     │
│  │ Pattern: Name:\s*([A-Z][a-z]+\s+[A-Z][a-z]+)   │     │
│  │                                                │     │
│  │ Example: "Name: Jon Mor" → "Jon Mor"           │     │
│  │                                                │     │
│  │ WHY: NO HARDCODING! Extract from document      │     │
│  └────────────────────────────────────────────────┘     │
│     ↓                                                     │
│  ┌────────────────────────────────────────────────┐     │
│  │ STEP 4: Build Metadata                         │     │
│  │ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │     │
│  │ metadata = {                                   │     │
│  │   "claim_id": "abc123...",                     │     │
│  │   "claim_number": "1",                         │     │
│  │   "claim_index": 0,                            │     │
│  │   "claimant_name": "Jon Mor", ← DYNAMIC        │     │
│  │   "title": "AUTO CLAIM FORM #1",               │     │
│  │   "source_type": "insurance_claim",            │     │
│  │   "parent_document_id": "...",                 │     │
│  │   "claim_total_characters": 1234,              │     │
│  │   "claim_total_words": 200,                    │     │
│  │   ...                                          │     │
│  │ }                                              │     │
│  └────────────────────────────────────────────────┘     │
│     ↓                                                     │
│  ┌────────────────────────────────────────────────┐     │
│  │ STEP 5: Create Document                        │     │
│  │ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │     │
│  │ Document(                                      │     │
│  │   text=claim_text,                             │     │
│  │   metadata=metadata,                           │     │
│  │   doc_id=claim_id                              │     │
│  │ )                                              │     │
│  └────────────────────────────────────────────────┘     │
│     ↓                                                     │
│  Output: List[Document] (one per claim)                 │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

### **Dynamic Claimant Name Extraction:**

```
WHY EXTRACT DYNAMICALLY?
─────────────────────────────────────────
✅ No hardcoding (works with any PDF)
✅ Enables filtering ("Jon Mor's phone?")
✅ Metadata carries to all chunks
✅ Agents can use name in queries


HOW IT WORKS:
─────────────────────────────────────────
Look at first 500 chars of claim text:
  "AUTO CLAIM FORM #1
   SECTION 1 – CLAIMANT INFORMATION
   Name: Jon Mor Account Number: 123456..."
          ↑      ↑
   Extract: "Jon Mor"

Pattern: Name:\s*([A-Z][a-z]+\s+[A-Z][a-z]+)
         followed by next field keyword

Handles:
  ✓ "Name: Jon Mor Account" → "Jon Mor"
  ✓ "Name: Jane Smith Address" → "Jane Smith"
  ✓ "Name: Bob Johnson Phone" → "Bob Johnson"

Stops at next field to avoid:
  ❌ "Name: Jon Mor Account Number: 123456"
       (would extract "Jon Mor Account Number")
```

---

### **Example: Creating Claim Documents**

```
Input:
─────────────────────────────────────────
Boundary 1: start=0, claim_number="1"
Boundary 2: start=500, claim_number="2"
Original document text (length 1000 chars)


Processing Claim 1:
─────────────────────────────────────────
1. Extract text:
   start=0, end=500
   claim_text = text[0:500]

2. Generate claim_id:
   "doc123_claim_0" → hash → "abc1234567890def"

3. Extract name:
   "Name: Jon Mor Account" → "Jon Mor"

4. Create Document:
   Document(
     text="AUTO CLAIM FORM #1\nName: Jon Mor...",
     metadata={
       "claim_id": "abc1234567890def",
       "claim_number": "1",
       "claim_index": 0,
       "claimant_name": "Jon Mor",
       "title": "AUTO CLAIM FORM #1",
       ...
     },
     doc_id="abc1234567890def"
   )


Processing Claim 2:
─────────────────────────────────────────
1. Extract text:
   start=500, end=1000
   claim_text = text[500:1000]

2. Generate claim_id:
   "doc123_claim_1" → hash → "def0987654321abc"

3. Extract name:
   "Name: Jane Smith Address" → "Jane Smith"

4. Create Document:
   Document(
     text="AUTO CLAIM FORM #2\nName: Jane Smith...",
     metadata={
       "claim_id": "def0987654321abc",
       "claim_number": "2",
       "claim_index": 1,
       "claimant_name": "Jane Smith",
       ...
     },
     doc_id="def0987654321abc"
   )
─────────────────────────────────────────

Output: [Document(claim #1), Document(claim #2)]
```

---

## 🎓 **Key Concepts**

### **1. Why Segmentation ≠ Chunking**

```
┌─────────────────────────────────────────────────────────┐
│         SEGMENTATION vs. CHUNKING                       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  SEGMENTATION:                                          │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│  • Business entity separation                           │
│  • One claim = one document                             │
│  • Claim-level isolation                                │
│  • Prevents cross-claim contamination                   │
│  • Happens BEFORE chunking                              │
│                                                         │
│  CHUNKING:                                              │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│  • Semantic unit creation                               │
│  • Text → Parent chunks → Child chunks                  │
│  • For embedding and retrieval                          │
│  • Happens AFTER segmentation                           │
│  • Operates on single-claim documents                   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

### **2. Deterministic Behavior**

```
DETERMINISTIC = REPRODUCIBLE:
─────────────────────────────────────────
Same PDF input → Same claims output

HOW:
  • Regex patterns (no ML randomness)
  • Hashed claim_ids (same hash every time)
  • Sorted boundaries (consistent order)

WHY:
  ✅ Debugging: Easy to reproduce issues
  ✅ Testing: Assertions won't flake
  ✅ Version control: Consistent across runs
  ✅ No model drift


NO MACHINE LEARNING:
─────────────────────────────────────────
Could we use ML? Yes, but:

Regex approach:
  ✅ Fast (milliseconds)
  ✅ Deterministic
  ✅ Explainable
  ✅ No training data needed
  ✅ No model to maintain

ML approach:
  ❌ Slow (seconds)
  ❌ Non-deterministic
  ❌ Black box
  ❌ Needs training data
  ❌ Model drift over time
```

---

### **3. Metadata Inheritance**

```
PARENT DOCUMENT METADATA:
─────────────────────────────────────────
document.metadata = {
  "document_type": "insurance_claim_form",
  "source_file": "claims_20.pdf",
  "language": "en",
  ...
}

EACH CLAIM DOCUMENT GETS:
─────────────────────────────────────────
claim_doc.metadata = {
  # Claim-specific (NEW):
  "claim_id": "abc123...",
  "claim_number": "1",
  "claim_index": 0,
  "claimant_name": "Jon Mor",
  "title": "AUTO CLAIM FORM #1",
  
  # Inherited from parent:
  "document_type": "insurance_claim_form",
  "source_file": "claims_20.pdf",
  "language": "en",
  
  # Parent reference:
  "parent_document_id": "doc123",
  ...
}

WHY:
  ✅ Traceability (which PDF did this come from?)
  ✅ Filtering (all claims from same PDF)
  ✅ Debugging (trace back to source)
```

---

### **4. Fallback Behavior**

```
ROBUST HANDLING:
─────────────────────────────────────────

Scenario 1: Multiple boundaries detected
  → Split into N claim documents ✅

Scenario 2: No boundaries detected
  → Treat entire PDF as 1 claim ✅
  → Better than failing!

Scenario 3: Empty text after boundary
  → Skip that claim (don't create empty doc) ✅

Scenario 4: Claimant name not found
  → claimant_name = None ✅
  → Still process the claim


GRACEFUL DEGRADATION:
─────────────────────────────────────────
Even if detection isn't perfect:
  ✅ System still works
  ✅ Single-claim PDFs handled
  ✅ No crashes or errors
  ✅ Worst case: treats as 1 big claim
```

---

## 📊 **Usage Examples**

### **Basic Usage:**

```python
from RAG.PDF_Ingestion import create_ingestion_pipeline
from RAG.Claim_Segmentation import create_claim_segmentation_pipeline

# Step 1: Ingest PDF
ingestion = create_ingestion_pipeline()
document = ingestion.ingest("claims_20.pdf")

print(f"PDF loaded: {len(document.text)} characters")
# Output: "PDF loaded: 50,000 characters"

# Step 2: Segment into claims
segmentation = create_claim_segmentation_pipeline()
claim_documents = segmentation.split_into_claims(document)

print(f"Found {len(claim_documents)} claims")
# Output: "Found 20 claims"

# Step 3: Inspect claims
for claim_doc in claim_documents:
    print(f"Claim #{claim_doc.metadata['claim_number']}: "
          f"{claim_doc.metadata['claimant_name']}")

# Output:
# Claim #1: Jon Mor
# Claim #2: Jane Smith
# Claim #3: Bob Johnson
# ...
# Claim #20: Sarah Lee
```

---

### **Integration Example:**

```python
from RAG.PDF_Ingestion import create_ingestion_pipeline
from RAG.Claim_Segmentation import create_claim_segmentation_pipeline
from RAG.Chunking_Layer import create_chunking_pipeline

# Full pipeline: PDF → Claims → Chunks
ingestion = create_ingestion_pipeline()
segmentation = create_claim_segmentation_pipeline()
chunking = create_chunking_pipeline()

# Stage 1: Ingest
document = ingestion.ingest("claims_20.pdf")

# Stage 2: Segment
claim_documents = segmentation.split_into_claims(document)

# Stage 3: Chunk each claim
all_nodes = []
for claim_doc in claim_documents:
    nodes = chunking.build_nodes(claim_doc)
    all_nodes.extend(nodes)
    print(f"Claim {claim_doc.metadata['claim_number']}: "
          f"{len(nodes)} nodes")

# Output:
# Claim 1: 28 nodes
# Claim 2: 25 nodes
# Claim 3: 30 nodes
# ...

print(f"Total nodes: {len(all_nodes)}")
# Output: "Total nodes: 550"

# All nodes have claim_id metadata for filtering!
```

---

## 🔗 **Downstream Impact**

### **How Claim Metadata is Used:**

```
1. CHUNKING LAYER:
   ─────────────────────────────────────────
   Each claim document → Separate node hierarchy
   All nodes tagged with claim_id

2. INDEX LAYER:
   ─────────────────────────────────────────
   Option A: Build separate index per claim
   Option B: Build one index, filter by claim_id

3. RETRIEVAL:
   ─────────────────────────────────────────
   Query: "Jon Mor's phone?"
   
   Filter: claim_id="001" OR claimant_name="Jon Mor"
   
   Only retrieve chunks from Jon's claim
   Never mix with Jane's or Bob's claims

4. AGENTS:
   ─────────────────────────────────────────
   Agent receives chunks with claim_id metadata
   Can verify all chunks are from same claim
   Prevents cross-claim hallucinations
```

---

## ✅ **Summary: Claim Segmentation Layer**

```
┌─────────────────────────────────────────────────────────┐
│        CLAIM SEGMENTATION SUMMARY                       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  PURPOSE:                                               │
│  Split multi-claim PDF → Separate claim documents      │
│                                                         │
│  INPUT:                                                 │
│  • Single Document (entire PDF, may have 20+ claims)    │
│                                                         │
│  OUTPUT:                                                │
│  • List[Document] (one per claim)                       │
│  • Each with claim_id and claimant_name metadata        │
│                                                         │
│  PROCESS:                                               │
│  1. Detect claim boundaries (regex patterns)            │
│  2. Extract text slices                                 │
│  3. Extract claimant names (dynamic, no hardcoding)     │
│  4. Create Documents with metadata                      │
│                                                         │
│  KEY FEATURES:                                          │
│  ✅ Deterministic (regex-based)                         │
│  ✅ Fast (milliseconds)                                 │
│  ✅ Robust (fallback to 1 claim if no boundaries)       │
│  ✅ Dynamic name extraction                             │
│  ✅ Metadata inheritance                                │
│                                                         │
│  ENABLES:                                               │
│  • Claim-level isolation                                │
│  • Independent processing per claim                     │
│  • Claim-specific filtering                             │
│  • No cross-claim contamination                         │
│                                                         │
│  PIPELINE POSITION:                                     │
│  PDF Ingestion → Claim Segmentation → Chunking         │
│                  ↑ YOU ARE HERE                         │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 📁 **Files**

| File | Purpose |
|------|---------|
| `claim_segmentation.py` | Main segmentation implementation |
| `__init__.py` | Module exports |
| `claim-segmentation-explained.md` | This documentation |

---

**Built for RagAgentv2 - Auto Claims RAG System** 🚗📄


RAG/Claim_Segmentation/claim-segmentation-explained.md
├─ 📄 What is the Claim Segmentation Layer?
├─ 🎯 Core Responsibility
│
├─ 🏗️ Why This Layer Exists
│   ├─ The Problem (without segmentation)
│   │   └─ Example: Cross-claim contamination
│   └─ The Solution (with segmentation)
│       └─ Example: Claim isolation
│
├─ 📍 Where It Fits in the Pipeline
│   ├─ Complete RAG pipeline position
│   └─ Why before chunking?
│
├─ 🔄 Claim Segmentation Process (2 Stages)
│   ├─ Overview diagram
│   │
│   ├─ Stage 1: Detect Claim Boundaries
│   │   ├─ Pattern 1: "AUTO CLAIM FORM #N"
│   │   ├─ Pattern 2: "Claim Number:" (fallback)
│   │   ├─ Pattern 3: Section headers (last resort)
│   │   ├─ Fallback: No boundaries detected
│   │   ├─ Detection flow diagram
│   │   └─ Example with real PDF text
│   │
│   └─ Stage 2: Create Claim Documents
│       ├─ Complete flow (5 steps)
│       ├─ Dynamic claimant name extraction
│       ├─ Metadata building
│       └─ Full example (2 claims)
│
├─ 🔍 Dynamic Claimant Name Extraction
│   ├─ Why extract dynamically?
│   ├─ How it works (regex patterns)
│   └─ Handling edge cases
│
├─ 📊 Example: Creating Claim Documents
│   └─ Complete step-by-step with 2 claims
│
├─ 🎓 Key Concepts
│   ├─ 1. Why Segmentation ≠ Chunking
│   ├─ 2. Deterministic Behavior
│   ├─ 3. Metadata Inheritance
│   └─ 4. Fallback Behavior
│
├─ 🔗 Downstream Impact
│   ├─ How claim metadata flows through system
│   ├─ Usage in Chunking Layer
│   ├─ Usage in Index Layer
│   ├─ Usage in Retrieval
│   └─ Usage in Agents
│
├─ 📊 Usage Examples
│   ├─ Basic usage
│   └─ Full pipeline integration
│
├─ ✅ Summary
└─ 📁 Files Reference



🎯 Key Takeaways:

1. PURPOSE:
   One PDF with 20 claims → 20 separate documents

2. WHY CRITICAL:
   Prevents mixing facts across different claims
   "Jon Mor's phone?" won't accidentally use Jane's phone!

3. WHERE IN PIPELINE:
   PDF Ingestion → Claim Segmentation → Chunking → Index

4. HOW IT WORKS:
   Regex patterns detect "AUTO CLAIM FORM #N"
   Extract text slices between boundaries
   Create separate Documents with metadata

5. DYNAMIC EXTRACTION:
   Claimant names extracted from text (no hardcoding!)

6. DETERMINISTIC:
   Same input → same output (regex, not ML)

7. ENABLES:
   • Claim-level isolation
   • Claim-specific filtering  
   • Independent processing per claim
   • No cross-claim contamination