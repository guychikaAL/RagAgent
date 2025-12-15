# RAGAS Evaluation - Complete Guide

## 📊 **What is RAGAS?**

**RAGAS** (Retrieval-Augmented Generation Assessment) is a **framework-agnostic evaluation library** specifically designed to evaluate RAG (Retrieval-Augmented Generation) systems. It provides automated, LLM-based metrics to assess both retrieval quality and generation quality.

```
┌─────────────────────────────────────────────────────────┐
│                RAGAS EVALUATION                         │
│       (Secondary Evaluation Framework)                  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  PURPOSE:                                               │
│  Automated evaluation of RAG system performance         │
│                                                         │
│  WHAT IT EVALUATES:                                     │
│  • Retrieval quality (precision, recall)                │
│  • Generation quality (faithfulness, relevancy)         │
│                                                         │
│  HOW:                                                   │
│  • Uses LLM (gpt-4o-mini) as evaluator                  │
│  • Compares system outputs against ground truth         │
│  • Provides automated scores (0.0 to 1.0)               │
│                                                         │
│  4 KEY METRICS:                                         │
│  1. Context Recall    (Did we retrieve ground truth?)   │
│  2. Context Precision (Are retrieved chunks relevant?)  │
│  3. Faithfulness      (Is answer grounded in context?)  │
│  4. Answer Relevancy  (Does answer address question?)   │
│                                                         │
│  CRITICAL:                                              │
│  ❌ NOT used during inference                           │
│  ❌ NOT a replacement for primary evaluation            │
│  ✅ Complements LLM-as-a-Judge evaluation               │
│  ✅ Provides additional insights                        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 🎯 **Why RAGAS?**

### **The Need for Automated RAG Evaluation:**

```
RAG SYSTEM CHALLENGES:
─────────────────────────────────────────

Traditional metrics (BLEU, ROUGE) don't work well for RAG:
  ❌ Can't evaluate retrieval quality
  ❌ Can't measure faithfulness (hallucination)
  ❌ Can't assess context relevance
  ❌ Don't understand semantic similarity

RAGAS solves this by:
  ✅ Using LLM as intelligent evaluator
  ✅ Evaluating both retrieval and generation
  ✅ Providing multiple complementary metrics
  ✅ Being framework-agnostic (works with any RAG system)
```

---

### **RAGAS vs. LLM-as-a-Judge:**

```
┌─────────────────────────────────────────────────────────┐
│       TWO EVALUATION APPROACHES                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  LLM-AS-A-JUDGE (Primary Evaluation):                  │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│  • Custom evaluation logic                              │
│  • Gemini 2.5-flash as judge                            │
│  • 3 metrics:                                           │
│    - Answer Correctness                                 │
│    - Context Relevancy                                  │
│    - Context Recall (expected chunks)                   │
│  • Tailored to our claims system                        │
│                                                         │
│                                                         │
│  RAGAS (Secondary Evaluation):                          │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│  • Standard evaluation framework                        │
│  • OpenAI gpt-4o-mini as evaluator                      │
│  • 4 metrics:                                           │
│    - Context Recall (ground truth attribution)          │
│    - Context Precision (ranking quality)                │
│    - Faithfulness (grounding)                           │
│    - Answer Relevancy (question alignment)              │
│  • Industry-standard, comparable                        │
│                                                         │
│                                                         │
│  WHY BOTH?                                              │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│  ✅ Different perspectives on system quality            │
│  ✅ Validate findings across frameworks                 │
│  ✅ Comprehensive evaluation coverage                   │
│  ✅ Industry-standard benchmarking (RAGAS)              │
│  ✅ Custom domain-specific checks (LLM-as-a-Judge)      │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 📏 **RAGAS Metrics Explained**

### **Metric 1: Context Recall**

```
┌─────────────────────────────────────────────────────────┐
│           CONTEXT RECALL                                │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  QUESTION:                                              │
│  Can the ground truth be attributed to the              │
│  retrieved contexts?                                    │
│                                                         │
│  FORMULA:                                               │
│  Recall = (GT sentences in contexts) / (Total GT sentences)│
│                                                         │
│  EXAMPLE:                                               │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│  Question: "What is Jon Mor's phone number?"            │
│                                                         │
│  Ground Truth: "555-1234"                               │
│                                                         │
│  Retrieved Contexts:                                    │
│    • Chunk 1: "Name: Jon Mor, Phone: 555-1234"         │
│    • Chunk 2: "Address: 123 Main St"                   │
│    • Chunk 3: "Accident date: 2024-01-24"              │
│                                                         │
│  Analysis:                                              │
│  LLM checks: Can "555-1234" be found in contexts?       │
│  Answer: YES (in Chunk 1)                               │
│  Score: 1.0 ✅                                          │
│                                                         │
│                                                         │
│  WHAT IT MEASURES:                                      │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│  • Retrieval completeness                               │
│  • Did we fetch the right information?                  │
│  • Are we missing key facts?                            │
│                                                         │
│  INTERPRETATION:                                        │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│  • 1.0: Perfect - all ground truth found                │
│  • 0.8: Good - most ground truth found                  │
│  • 0.5: Moderate - half of ground truth missing         │
│  • 0.0: Poor - ground truth not in contexts             │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

### **Metric 2: Context Precision**

```
┌─────────────────────────────────────────────────────────┐
│           CONTEXT PRECISION                             │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  QUESTION:                                              │
│  Are the relevant contexts ranked higher than           │
│  irrelevant ones?                                       │
│                                                         │
│  FORMULA:                                               │
│  Precision@k = (Relevant contexts in top-k) / k         │
│                                                         │
│  EXAMPLE:                                               │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│  Question: "What is the claim amount?"                  │
│                                                         │
│  Ground Truth: "$5,000"                                 │
│                                                         │
│  Retrieved Contexts (in order):                         │
│    1. "Claim Amount: $5,000" ✅ RELEVANT                │
│    2. "Approved on 2024-02-18" ✅ RELEVANT              │
│    3. "Name: Jon Mor" ❌ NOT RELEVANT                   │
│                                                         │
│  Analysis:                                              │
│  LLM checks each chunk:                                 │
│  • Chunk 1: Relevant to question                        │
│  • Chunk 2: Relevant to question                        │
│  • Chunk 3: Not relevant to question                    │
│                                                         │
│  Precision calculation:                                 │
│  Top-1: 1/1 = 1.0                                       │
│  Top-2: 2/2 = 1.0                                       │
│  Top-3: 2/3 = 0.67                                      │
│  Average: ~0.89 ✅                                      │
│                                                         │
│                                                         │
│  WHAT IT MEASURES:                                      │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│  • Retrieval accuracy                                   │
│  • Signal-to-noise ratio                                │
│  • Are we fetching irrelevant chunks?                   │
│                                                         │
│  INTERPRETATION:                                        │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│  • 1.0: Perfect - all top chunks relevant               │
│  • 0.8: Good - most top chunks relevant                 │
│  • 0.5: Moderate - half of top chunks irrelevant        │
│  • 0.0: Poor - all chunks irrelevant                    │
│                                                         │
│  WHY IT MATTERS:                                        │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│  Low precision → Wasting tokens on irrelevant context   │
│  High precision → Efficient, focused retrieval          │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

### **Metric 3: Faithfulness**

```
┌─────────────────────────────────────────────────────────┐
│             FAITHFULNESS                                │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  QUESTION:                                              │
│  Is the generated answer grounded in the                │
│  retrieved contexts? (No hallucination?)                │
│                                                         │
│  FORMULA:                                               │
│  Faithfulness = (Supported claims) / (Total claims)     │
│                                                         │
│  EXAMPLE:                                               │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│  Question: "What happened in the accident?"             │
│                                                         │
│  Retrieved Contexts:                                    │
│    • "Accident on 2024-01-24 at Main St"               │
│    • "Vehicle damage: front bumper"                     │
│                                                         │
│  Generated Answer:                                      │
│  "The accident occurred on January 24, 2024 at         │
│   Main Street. The vehicle's front bumper was damaged." │
│                                                         │
│  Analysis:                                              │
│  LLM breaks answer into claims:                         │
│    1. "Accident on January 24, 2024" ✅ (in context)   │
│    2. "At Main Street" ✅ (in context)                 │
│    3. "Front bumper damaged" ✅ (in context)           │
│                                                         │
│  Faithfulness: 3/3 = 1.0 ✅ (Perfect!)                 │
│                                                         │
│                                                         │
│  COUNTER-EXAMPLE (Hallucination):                      │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│  Generated Answer (BAD):                                │
│  "The accident occurred on January 24, 2024 at         │
│   Main Street. The driver was speeding and ran a       │
│   red light."                                           │
│                                                         │
│  Analysis:                                              │
│    1. "Accident on January 24, 2024" ✅ (in context)   │
│    2. "At Main Street" ✅ (in context)                 │
│    3. "Driver was speeding" ❌ (NOT in context!)       │
│    4. "Ran a red light" ❌ (NOT in context!)           │
│                                                         │
│  Faithfulness: 2/4 = 0.5 ❌ (Hallucination detected!)  │
│                                                         │
│                                                         │
│  WHAT IT MEASURES:                                      │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│  • Hallucination detection                              │
│  • Answer grounding                                     │
│  • Factual accuracy                                     │
│                                                         │
│  INTERPRETATION:                                        │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│  • 1.0: Perfect - no hallucination                      │
│  • 0.8: Good - minor unsupported claims                 │
│  • 0.5: Moderate - significant hallucination            │
│  • 0.0: Poor - completely made up answer                │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

### **Metric 4: Answer Relevancy**

```
┌─────────────────────────────────────────────────────────┐
│           ANSWER RELEVANCY                              │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  QUESTION:                                              │
│  Does the answer address the user's question?           │
│  Is it relevant and complete?                           │
│                                                         │
│  HOW IT WORKS:                                          │
│  LLM generates questions from the answer,               │
│  then compares similarity to original question          │
│                                                         │
│  EXAMPLE:                                               │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│  Original Question:                                     │
│  "What is Jon Mor's phone number?"                      │
│                                                         │
│  Generated Answer:                                      │
│  "Jon Mor's phone number is 555-1234."                  │
│                                                         │
│  Analysis:                                              │
│  LLM generates questions from answer:                   │
│    • "What is Jon Mor's phone number?" ✅              │
│                                                         │
│  Similarity to original: Very high!                     │
│  Score: 0.95 ✅                                         │
│                                                         │
│                                                         │
│  COUNTER-EXAMPLE (Low Relevancy):                       │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│  Original Question:                                     │
│  "What is Jon Mor's phone number?"                      │
│                                                         │
│  Generated Answer (BAD):                                │
│  "Jon Mor filed a claim on 2024-01-24 for a            │
│   vehicle accident. The claim was approved."            │
│                                                         │
│  Analysis:                                              │
│  LLM generates questions from answer:                   │
│    • "When did Jon Mor file a claim?" ❌               │
│    • "Was the claim approved?" ❌                       │
│                                                         │
│  Similarity to original: Very low!                      │
│  (Answer doesn't address phone number)                  │
│  Score: 0.2 ❌                                          │
│                                                         │
│                                                         │
│  WHAT IT MEASURES:                                      │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│  • Answer completeness                                  │
│  • Question-answer alignment                            │
│  • Answer focus                                         │
│                                                         │
│  INTERPRETATION:                                        │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│  • 1.0: Perfect - directly answers question             │
│  • 0.8: Good - mostly answers question                  │
│  • 0.5: Moderate - partially answers                    │
│  • 0.0: Poor - doesn't address question                 │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 🔄 **RAGAS Evaluation Flow**

### **Complete Pipeline:**

```
┌──────────────────────────────────────────────────────────┐
│         RAGAS EVALUATION PIPELINE (7 STEPS)              │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Input: Test Cases (test_cases.json)                    │
│     ↓                                                     │
│  ┌────────────────────────────────────────────────┐     │
│  │ STEP 1: Load Test Cases                        │     │
│  │ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │     │
│  │ Load from: evaluation/test_cases.json          │     │
│  │ Each test case has:                            │     │
│  │   • question                                   │     │
│  │   • ground_truth                               │     │
│  │   • expected_chunks                            │     │
│  │                                                │     │
│  │ Example:                                       │     │
│  │ {                                              │     │
│  │   "id": "q1",                                  │     │
│  │   "question": "What is Jon Mor's phone?",      │     │
│  │   "ground_truth": "555-1234"                   │     │
│  │ }                                              │     │
│  └────────────────────────────────────────────────┘     │
│     ↓                                                     │
│  ┌────────────────────────────────────────────────┐     │
│  │ STEP 2: Initialize RAG System                  │     │
│  │ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │     │
│  │ • Load production index                        │     │
│  │ • Create retrievers (needle, summary)          │     │
│  │ • Initialize agents (router, needle, summary)  │     │
│  │ • Create orchestrator                          │     │
│  │                                                │     │
│  │ WHY: Need working RAG system to evaluate       │     │
│  └────────────────────────────────────────────────┘     │
│     ↓                                                     │
│  ┌────────────────────────────────────────────────┐     │
│  │ STEP 3: Query RAG System                       │     │
│  │ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │     │
│  │ For each test case:                            │     │
│  │   1. Send question to orchestrator             │     │
│  │   2. Collect answer                            │     │
│  │   3. Collect retrieved contexts (chunk texts)  │     │
│  │   4. Collect metadata                          │     │
│  │                                                │     │
│  │ Result:                                        │     │
│  │   {                                            │     │
│  │     "answer": "555-1234",                      │     │
│  │     "contexts": ["Phone: 555-1234", ...],      │     │
│  │     "sources": ["chunk_123", ...]              │     │
│  │   }                                            │     │
│  └────────────────────────────────────────────────┘     │
│     ↓                                                     │
│  ┌────────────────────────────────────────────────┐     │
│  │ STEP 4: Build RAGAS Dataset                    │     │
│  │ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │     │
│  │ Combine into Hugging Face Dataset:             │     │
│  │ {                                              │     │
│  │   "question": [...],                           │     │
│  │   "answer": [...],                             │     │
│  │   "contexts": [...],  # List of chunk texts    │     │
│  │   "ground_truth": [...]                        │     │
│  │ }                                              │     │
│  │                                                │     │
│  │ WHY: RAGAS requires this specific format       │     │
│  └────────────────────────────────────────────────┘     │
│     ↓                                                     │
│  ┌────────────────────────────────────────────────┐     │
│  │ STEP 5: Initialize Evaluator LLM               │     │
│  │ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │     │
│  │ LLM: OpenAI gpt-4o-mini                        │     │
│  │ Temperature: 0.0 (deterministic)               │     │
│  │ Timeout: 60s                                   │     │
│  │ Max Retries: 3                                 │     │
│  │                                                │     │
│  │ WHY gpt-4o-mini:                               │     │
│  │   • Fast and cost-effective                    │     │
│  │   • More stable than Gemini experimental       │     │
│  │   • Reliable for evaluation                    │     │
│  └────────────────────────────────────────────────┘     │
│     ↓                                                     │
│  ┌────────────────────────────────────────────────┐     │
│  │ STEP 6: Run RAGAS Evaluation                   │     │
│  │ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │     │
│  │ For each test case:                            │     │
│  │   For each metric:                             │     │
│  │     • LLM evaluates                            │     │
│  │     • Returns score (0.0 to 1.0)               │     │
│  │                                                │     │
│  │ Metrics evaluated:                             │     │
│  │   1. context_recall                            │     │
│  │   2. context_precision                         │     │
│  │   3. faithfulness                              │     │
│  │   4. answer_relevancy                          │     │
│  │                                                │     │
│  │ WHY: Each metric provides different insight    │     │
│  └────────────────────────────────────────────────┘     │
│     ↓                                                     │
│  ┌────────────────────────────────────────────────┐     │
│  │ STEP 7: Save Results                           │     │
│  │ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │     │
│  │ Save to: ragas_results.json                    │     │
│  │                                                │     │
│  │ Format:                                        │     │
│  │ {                                              │     │
│  │   "results": [                                 │     │
│  │     {                                          │     │
│  │       "question_id": "q1",                     │     │
│  │       "context_recall": 1.0,                   │     │
│  │       "context_precision": 0.89,               │     │
│  │       "faithfulness": 1.0,                     │     │
│  │       "answer_relevancy": 0.95                 │     │
│  │     },                                         │     │
│  │     ...                                        │     │
│  │   ],                                           │     │
│  │   "summary": {                                 │     │
│  │     "avg_context_recall": 0.95,                │     │
│  │     "avg_context_precision": 0.87,             │     │
│  │     "avg_faithfulness": 0.99,                  │     │
│  │     "avg_answer_relevancy": 0.92               │     │
│  │   }                                            │     │
│  │ }                                              │     │
│  └────────────────────────────────────────────────┘     │
│     ↓                                                     │
│  Output: ragas_results.json + Summary printed           │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## 🎓 **Key Concepts**

### **1. LLM as Evaluator**

```
WHY USE LLM FOR EVALUATION?
─────────────────────────────────────────

Traditional metrics (BLEU, ROUGE):
  ❌ Can't understand semantic similarity
  ❌ Can't detect hallucination
  ❌ Can't evaluate context relevance
  ❌ Too rigid for RAG evaluation

LLM as evaluator (RAGAS approach):
  ✅ Understands semantic meaning
  ✅ Can reason about relevance
  ✅ Can detect hallucination
  ✅ Flexible, human-like judgment

EXAMPLE:
─────────────────────────────────────────
Question: "What is Jon Mor's phone?"
Ground Truth: "555-1234"
System Answer: "The phone number is 555-1234"

BLEU Score: Low (different wording)
LLM Evaluation: High (same meaning)
```

---

### **2. Framework-Agnostic**

```
RAGAS WORKS WITH ANY RAG SYSTEM:
─────────────────────────────────────────

Only needs 4 inputs:
  1. question
  2. answer (generated by RAG system)
  3. contexts (retrieved chunks)
  4. ground_truth (expected answer)

Works with:
  ✅ LlamaIndex
  ✅ LangChain
  ✅ Haystack
  ✅ Custom RAG systems
  ✅ Any retrieval + generation pipeline

WHY: Standard evaluation across tools
```

---

### **3. Offline Analysis Only**

```
RAGAS IS NOT USED DURING INFERENCE:
─────────────────────────────────────────

┌────────────────────────────────────┐
│ INFERENCE TIME (Real queries)     │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│ User → RAG System → Answer         │
│ (No RAGAS involved)                │
└────────────────────────────────────┘

┌────────────────────────────────────┐
│ EVALUATION TIME (Test suite)      │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│ Test Cases → RAG System → Answers  │
│            ↓                       │
│         RAGAS Evaluation           │
│            ↓                       │
│         Scores + Insights          │
└────────────────────────────────────┘

WHY OFFLINE:
  ✅ No latency impact on users
  ✅ Detailed analysis without time pressure
  ✅ Batch evaluation of test suite
  ✅ Comprehensive metrics
```

---

### **4. Complementary to LLM-as-a-Judge**

```
TWO EVALUATION FRAMEWORKS:
─────────────────────────────────────────

LLM-as-a-Judge:
  • Custom evaluation logic
  • Domain-specific (insurance claims)
  • Gemini 2.5-flash
  • Expected chunks validation

RAGAS:
  • Standard evaluation framework
  • General RAG evaluation
  • OpenAI gpt-4o-mini
  • Ground truth attribution

TOGETHER:
  ✅ Cross-validate findings
  ✅ Multiple perspectives
  ✅ Comprehensive coverage
  ✅ Industry-standard + custom
```

---

## 📊 **Usage Examples**

### **Running RAGAS Evaluation:**

```bash
# From project root
cd evaluation-ragas

# Install dependencies
pip install -r requirements.txt

# Set API key
export OPENAI_API_KEY="your-openai-key"

# Run evaluation
python ragas_eval.py

# Expected output:
# ================================================================
# 🔑 Checking API Keys...
# ================================================================
# ✅ OPENAI_API_KEY found
#
# 🔧 Initializing RAG system...
# ...
# 📊 Building RAGAS dataset from 8 test cases...
# ...
# 🔬 Running RAGAS evaluation...
# ...
# ✅ Results saved to: ragas_results.json
#
# ======================================================================
# 📊 RAGAS EVALUATION SUMMARY
# ======================================================================
# Total test cases: 8
#
# Average Scores:
#   context_recall: 0.950
#   context_precision: 0.870
#   faithfulness: 0.990
#   answer_relevancy: 0.920
# ======================================================================
```

---

### **Visualizing Results:**

```bash
# Generate visualization
python visualize_results.py

# Creates: ragas_visualization.png
# Shows:
# - Overall metric scores (bar chart)
# - Context precision by question (bar chart)
# - Answer relevancy by question (bar chart)
# - Heatmap of all metrics by question
```

---

### **Viewing Results in GUI:**

```bash
# From project root
streamlit run app/gui_app.py

# In GUI:
# 1. Click "Run RAGAS Evaluation"
# 2. Wait for completion
# 3. Click "Show RAGAS Charts"
# 4. Click "Compare Evaluations" (LLM-as-a-Judge vs. RAGAS)
```

---

## 🔍 **Interpreting Results**

### **Score Thresholds:**

```
METRIC SCORE INTERPRETATION:
─────────────────────────────────────────

🟢 Excellent: 0.9 - 1.0
  • System performing very well
  • Minor improvements only

🟡 Good: 0.7 - 0.9
  • System performing adequately
  • Room for improvement

🟠 Moderate: 0.5 - 0.7
  • System has significant issues
  • Needs attention

🔴 Poor: 0.0 - 0.5
  • System failing on this metric
  • Critical issues to fix
```

---

### **Example Analysis:**

```
SAMPLE RESULTS:
─────────────────────────────────────────
context_recall: 0.950 🟢 Excellent
context_precision: 0.870 🟡 Good
faithfulness: 0.990 🟢 Excellent
answer_relevancy: 0.920 🟢 Excellent


INTERPRETATION:
─────────────────────────────────────────

✅ STRENGTHS:
  • High context_recall (0.95)
    → Retrieving ground truth effectively
    → Chunking and indexing working well

  • Excellent faithfulness (0.99)
    → No hallucination
    → Answers grounded in context
    → Agents following instructions

  • High answer_relevancy (0.92)
    → Answers addressing questions
    → Good answer formatting


⚠️  AREAS FOR IMPROVEMENT:
  • Context_precision (0.87)
    → Some irrelevant chunks retrieved
    → Can improve similarity_threshold
    → Can tune top_k parameter

RECOMMENDATIONS:
  1. Increase similarity_threshold from 0.75 to 0.80
  2. Monitor precision vs. recall trade-off
  3. Test with adjusted parameters
```

---

## ⚙️ **Configuration**

### **Retriever Settings:**

```python
# In ragas_eval.py:

# Needle Retriever (for atomic facts)
needle_retriever = index_manager.get_needle_retriever(
    top_k=3,              # Fewer chunks (precision)
    similarity_threshold=0.75,  # Higher threshold (quality)
)

# MapReduce Query Engine (for comprehensive answers)
map_reduce_query_engine = index_manager.get_map_reduce_query_engine(
    top_k=15,  # More chunks (recall)
)

# WHY THESE SETTINGS:
# - Optimized from evaluation results
# - Balances precision and recall
# - Different strategies for different question types
```

---

### **Evaluation LLM:**

```python
# In ragas_eval.py:

self.llm = ChatOpenAI(
    model="gpt-4o-mini",  # Fast, cost-effective
    api_key=api_key,
    temperature=0.0,      # Deterministic evaluation
    timeout=60,           # 60s timeout per call
    max_retries=3,        # Retry on failures
)

# WHY gpt-4o-mini:
# ✅ More stable than Gemini experimental models
# ✅ Fast and cost-effective
# ✅ Reliable for evaluation
# ✅ Good performance on evaluation tasks
```

---

## ✅ **Summary: RAGAS Evaluation**

```
┌─────────────────────────────────────────────────────────┐
│            RAGAS EVALUATION SUMMARY                     │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  WHAT:                                                  │
│  Framework-agnostic RAG evaluation library              │
│                                                         │
│  PURPOSE:                                               │
│  Automated, LLM-based evaluation of RAG systems         │
│                                                         │
│  4 KEY METRICS:                                         │
│  1. Context Recall    (Retrieval completeness)          │
│  2. Context Precision (Retrieval accuracy)              │
│  3. Faithfulness      (No hallucination)                │
│  4. Answer Relevancy  (Question alignment)              │
│                                                         │
│  HOW IT WORKS:                                          │
│  1. Load test cases                                     │
│  2. Query RAG system                                    │
│  3. Collect outputs (answer, contexts)                  │
│  4. Build RAGAS dataset                                 │
│  5. Run evaluation (gpt-4o-mini as judge)               │
│  6. Save results to JSON                                │
│                                                         │
│  EVALUATOR LLM:                                         │
│  OpenAI gpt-4o-mini (different from RAG system)         │
│                                                         │
│  USAGE:                                                 │
│  • Offline analysis only                                │
│  • NOT used during inference                            │
│  • Complements LLM-as-a-Judge evaluation                │
│  • Provides industry-standard metrics                   │
│                                                         │
│  OUTPUT:                                                │
│  • ragas_results.json (detailed scores)                 │
│  • ragas_visualization.png (charts)                     │
│  • Summary metrics (printed)                            │
│                                                         │
│  INTEGRATION:                                           │
│  • GUI "Run RAGAS Evaluation" button                    │
│  • Automated evaluation pipeline                        │
│  • Comparison with LLM-as-a-Judge                       │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 📁 **Files**

| File | Purpose |
|------|---------|
| `ragas_eval.py` | Main evaluation script |
| `ragas_metrics.py` | Metric definitions |
| `visualize_results.py` | Result visualization |
| `ragas_results.json` | Evaluation results (generated) |
| `ragas_visualization.png` | Charts (generated) |
| `requirements.txt` | Dependencies |
| `evaluation-ragas-explained.md` | This documentation |

---

## 🎯 **Key Takeaways**

```
1. RAGAS = RETRIEVAL-AUGMENTED GENERATION ASSESSMENT:
   Automated evaluation framework for RAG systems.

2. 4 KEY METRICS:
   • Context Recall: Did we retrieve ground truth?
   • Context Precision: Are retrieved chunks relevant?
   • Faithfulness: Is answer grounded (no hallucination)?
   • Answer Relevancy: Does answer address question?

3. LLM AS EVALUATOR:
   Uses gpt-4o-mini to judge quality (semantic understanding).

4. FRAMEWORK-AGNOSTIC:
   Works with any RAG system (LlamaIndex, LangChain, custom).

5. OFFLINE ANALYSIS:
   NOT used during inference.
   Batch evaluation of test suite.

6. COMPLEMENTS LLM-AS-A-JUDGE:
   Two perspectives = comprehensive evaluation.

7. 7-STEP PIPELINE:
   Load → Initialize → Query → Build Dataset → Evaluate → Save

8. INTERPRETING SCORES:
   0.9-1.0: Excellent ✅
   0.7-0.9: Good 🟡
   0.5-0.7: Moderate ⚠️
   0.0-0.5: Poor ❌

9. CONFIGURATION:
   Tune retriever settings (top_k, similarity_threshold)
   based on precision/recall trade-offs.

10. OUTPUT:
    JSON results + visualization + summary metrics.
```

---

**Built for RagAgentv2 - Auto Claims RAG System** 📊🔬

🎯 Key Takeaways:

1. RAGAS = RETRIEVAL-AUGMENTED GENERATION ASSESSMENT:
   Automated evaluation framework for RAG systems.
   Uses LLM (gpt-4o-mini) as intelligent evaluator.

2. 4 KEY METRICS:
   • Context Recall: "Did we retrieve ground truth?"
     Example: Ground truth "555-1234" in retrieved chunks? YES → 1.0
   
   • Context Precision: "Are retrieved chunks relevant?"
     Example: 2 relevant, 1 irrelevant in top-3 → 0.67
   
   • Faithfulness: "Is answer grounded? (No hallucination?)"
     Example: All answer claims supported by context → 1.0
   
   • Answer Relevancy: "Does answer address question?"
     Example: Answer directly addresses phone question → 0.95

3. HOW IT WORKS (7 STEPS):
   1. Load test cases (test_cases.json)
   2. Initialize RAG system (index, agents)
   3. Query RAG system (get answers + contexts)
   4. Build RAGAS dataset (HuggingFace format)
   5. Initialize evaluator LLM (gpt-4o-mini)
   6. Run evaluation (each metric, each question)
   7. Save results (ragas_results.json)

4. LLM AS EVALUATOR:
   Why better than BLEU/ROUGE:
   ✅ Understands semantic similarity
   ✅ Can detect hallucination
   ✅ Can reason about relevance
   ✅ Human-like judgment

5. FRAMEWORK-AGNOSTIC:
   Works with ANY RAG system:
   • LlamaIndex ✅
   • LangChain ✅
   • Custom RAG ✅
   Only needs: question, answer, contexts, ground_truth

6. OFFLINE ANALYSIS ONLY:
   NOT used during inference!
   Batch evaluation of test suite.
   No latency impact on users.

7. VS. LLM-AS-A-JUDGE:
   LLM-as-a-Judge: Custom, domain-specific, Gemini
   RAGAS: Standard, general RAG, OpenAI
   → Use BOTH for comprehensive evaluation!

8. SCORE INTERPRETATION:
   0.9-1.0: Excellent 🟢 (System performing very well)
   0.7-0.9: Good 🟡 (Room for improvement)
   0.5-0.7: Moderate ⚠️ (Significant issues)
   0.0-0.5: Poor 🔴 (Critical issues)

9. CONFIGURATION:
   needle_retriever: top_k=3, threshold=0.75 (precision)
   map_reduce: top_k=15 (recall)
   LLM: gpt-4o-mini, temp=0.0, timeout=60s

10. OUTPUT:
    • ragas_results.json (detailed scores per question)
    • ragas_visualization.png (charts)
    • Summary metrics (printed)
    • GUI integration (compare evaluations)