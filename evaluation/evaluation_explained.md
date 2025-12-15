# LLM-as-a-Judge Evaluation - Complete Guide

## 📊 **What is LLM-as-a-Judge?**

LLM-as-a-Judge is an automated evaluation method where an **independent AI model** (Gemini) evaluates the quality of your RAG system's answers. It's like having a teacher grade your homework - but the teacher is another AI that doesn't know what you're trying to do, so it's fair!

---

## 🎯 **The Big Picture**

```
┌─────────────────────────────────────────────────────────┐
│               LLM-AS-A-JUDGE EVALUATION                 │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1. Test Cases (questions + ground truth)              │
│            ↓                                            │
│  2. Run through YOUR RAG system (OpenAI)               │
│            ↓                                            │
│  3. Collect: answer, route, chunks, confidence         │
│            ↓                                            │
│  4. Send to GEMINI JUDGE (independent evaluator)       │
│            ↓                                            │
│  5. Judge scores 3 metrics (A, B, C)                   │
│            ↓                                            │
│  6. Aggregate scores → Final evaluation                │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 🔄 **The 7-Step Evaluation Pipeline**

### **Step 1: Load Test Cases**

Test cases are stored in `test_cases.json`:

```json
{
  "id": "q1",
  "type": "needle",
  "question": "What is Jon Mor's phone number?",
  "ground_truth": "555-1234",
  "expected_chunks": ["chunk_id_1", "chunk_id_2"]
}
```

**What each test case contains:**
- ✅ **Question**: What to ask the RAG system
- ✅ **Ground Truth**: The correct answer
- ✅ **Expected Chunks**: Which chunks should be retrieved
- ✅ **Type**: NEEDLE (specific fact) or SUMMARY (broad question)

---

### **Step 2: Run Through RAG System**

Each question is processed by your RAG system:

```python
# Your system processes the question
result = orchestrator.run("What is Jon Mor's phone number?")

# Returns:
{
  "answer": "555-1234",
  "route": "NEEDLE",
  "sources": ["chunk_id_1"],
  "confidence": 0.95,
  "retrieved_chunks_content": ["Chunk text..."]
}
```

**What happens internally:**
1. ✅ **Router Agent** decides: NEEDLE or SUMMARY
2. ✅ **Retriever** finds relevant chunks from vector database
3. ✅ **Agent** (Needle or Summary) generates answer
4. ✅ **System** returns answer + metadata

---

### **Step 3: Collect Results**

For EACH test case, the system collects:

| Data Point | Example | Purpose |
|------------|---------|---------|
| **System Answer** | "555-1234" | What your RAG returned |
| **Route** | "NEEDLE" | Which agent was used |
| **Retrieved Chunks** | ["chunk_1", "chunk_2"] | What chunks were used |
| **Confidence** | 0.95 | System's confidence score |
| **Chunk Content** | "Jon Mor: 555-1234" | Actual text of chunks |

---

### **Step 4: Initialize Gemini Judge**

```python
judge = GeminiJudge(model="gemini-2.5-flash")
```

**Why use Gemini instead of OpenAI?**

```
RAG System → Uses OpenAI (gpt-4o-mini)
Judge      → Uses Gemini (gemini-2.5-flash)
             ↑ Different model = Unbiased evaluation
```

**Key Benefits:**
- ✅ **Independent perspective**: Not "marking its own homework"
- ✅ **Avoids bias**: Different model, different training data
- ✅ **Unbiased scoring**: Doesn't favor OpenAI-style answers
- ✅ **Industry standard**: Best practice for RAG evaluation

---

### **Step 5: Evaluate 3 Metrics**

The judge evaluates **3 separate metrics** for each test case. Each metric gets a score of **0.0**, **0.5**, or **1.0**.

---

#### **📊 Metric A: ANSWER CORRECTNESS**

**Question:** *"Did the system give the right answer?"*

```
┌─────────────────────────────────────────┐
│ INPUT TO JUDGE:                         │
├─────────────────────────────────────────┤
│ Question: "What is Jon Mor's phone?"    │
│ Ground Truth: "555-1234"                │
│ System Answer: "555-1234"               │
└─────────────────────────────────────────┘
           ↓ GEMINI JUDGE ↓
┌─────────────────────────────────────────┐
│ OUTPUT:                                 │
├─────────────────────────────────────────┤
│ Score: 1.0 (Fully Correct)              │
│ Explanation: "System answer matches     │
│              ground truth exactly."     │
└─────────────────────────────────────────┘
```

**Scoring Guidelines:**

| Score | Meaning | Criteria |
|-------|---------|----------|
| **1.0** | Fully Correct | ✅ Matches ground truth exactly<br>✅ All key facts present<br>✅ No contradictions<br>✅ No hallucinations |
| **0.5** | Partially Correct | ⚠️ Some facts match, some missing<br>⚠️ Correct direction but incomplete<br>⚠️ Minor contradictions |
| **0.0** | Incorrect | ❌ Wrong answer<br>❌ Contradicts ground truth<br>❌ Hallucinates facts<br>❌ Says "I don't know" when answer exists |

**Judge Prompt (Simplified):**
```
You are an ANSWER CORRECTNESS evaluator.

Compare:
1. GROUND TRUTH (correct answer)
2. SYSTEM ANSWER (what RAG returned)

Rules:
⚠️ DO NOT use external knowledge
⚠️ ONLY compare what is explicitly stated
⚠️ Be CONSERVATIVE - penalize weak matches

Return ONLY JSON:
{
  "score": 1.0 or 0.5 or 0.0,
  "explanation": "..."
}
```

---

#### **📊 Metric B: CONTEXT RELEVANCY**

**Question:** *"Did the system use relevant chunks?"*

```
┌─────────────────────────────────────────┐
│ INPUT TO JUDGE:                         │
├─────────────────────────────────────────┤
│ Question: "What is Jon Mor's phone?"    │
│ Question Type: "needle"                 │
│ Retrieved Chunks:                       │
│   - "Jon Mor, phone: 555-1234"          │
│   - "Address: 123 Main St"              │
└─────────────────────────────────────────┘
           ↓ GEMINI JUDGE ↓
┌─────────────────────────────────────────┐
│ OUTPUT:                                 │
├─────────────────────────────────────────┤
│ Score: 1.0 (Highly Relevant)            │
│ Explanation: "Chunks contain phone      │
│              number info, relevant."    │
└─────────────────────────────────────────┘
```

**Scoring Guidelines:**

| Score | Meaning | Criteria |
|-------|---------|----------|
| **1.0** | Highly Relevant | ✅ All chunks semantically related to question<br>✅ Chunks contain needed information<br>✅ No irrelevant chunks<br>✅ Appropriate chunk types for question |
| **0.5** | Partially Relevant | ⚠️ Some chunks relevant, some not<br>⚠️ Relevant info mixed with noise<br>⚠️ Suboptimal chunk types |
| **0.0** | Not Relevant | ❌ Chunks don't address question<br>❌ Wrong topic entirely<br>❌ No useful information |

**What This Metric Evaluates:**

For **NEEDLE questions** (specific facts):
- Should retrieve: Atomic, precise child chunks
- Focus: High precision (exact facts)
- Example: "What is the phone number?" → Chunk with phone number only

For **SUMMARY questions** (broad context):
- Should retrieve: Broader parent/merged chunks
- Focus: High recall (comprehensive context)
- Example: "Describe the incident" → Multiple chunks with event details

**Judge Prompt (Simplified):**
```
You are a CONTEXT RELEVANCY evaluator.

Evaluate whether the system used the RIGHT chunks.

Rules:
⚠️ Evaluate ONLY semantic relevance to question
⚠️ DO NOT evaluate if answer was correct
⚠️ Be STRICT - penalize irrelevant chunks

Return ONLY JSON:
{
  "score": 1.0 or 0.5 or 0.0,
  "explanation": "..."
}
```

---

#### **📊 Metric C: CONTEXT RECALL**

**Question:** *"Did the system retrieve the expected chunks?"*

```
┌─────────────────────────────────────────┐
│ INPUT TO JUDGE:                         │
├─────────────────────────────────────────┤
│ Question: "What is Jon Mor's phone?"    │
│ Expected Chunks:                        │
│   - chunk_id_1                          │
│   - chunk_id_2                          │
│ Actually Retrieved:                     │
│   - chunk_id_1                          │
│   - chunk_id_5                          │
└─────────────────────────────────────────┘
           ↓ GEMINI JUDGE ↓
┌─────────────────────────────────────────┐
│ OUTPUT:                                 │
├─────────────────────────────────────────┤
│ Score: 0.5 (Partial Recall)             │
│ Explanation: "Got chunk_id_1 but        │
│              missed chunk_id_2."        │
└─────────────────────────────────────────┘
```

**Scoring Guidelines:**

| Score | Meaning | Criteria |
|-------|---------|----------|
| **1.0** | Perfect Recall | ✅ ALL expected chunks retrieved<br>✅ No missing necessary chunks |
| **0.5** | Partial Recall | ⚠️ SOME expected chunks retrieved<br>⚠️ Some necessary chunks missing |
| **0.0** | No Recall | ❌ NONE of expected chunks retrieved<br>❌ All necessary chunks missing |

**Important Notes:**
- ✅ This metric is **independent** of answer correctness
- ✅ It only checks: "Were the right chunks retrieved?"
- ✅ Even if answer is correct, recall can be low (if wrong chunks were used)
- ✅ Even if answer is wrong, recall can be high (if right chunks were retrieved)

**Judge Prompt (Simplified):**
```
You are a CONTEXT RECALL evaluator.

Evaluate whether the expected chunks were retrieved.

Rules:
⚠️ Compare retrieved chunks to expected chunks
⚠️ DO NOT evaluate answer quality
⚠️ ONLY check if expected chunks are present

Return ONLY JSON:
{
  "score": 1.0 or 0.5 or 0.0,
  "explanation": "..."
}
```

---

### **Step 6: Aggregate Scores**

For each test case, compute the **final score** as the average of all 3 metrics:

```python
final_score = (
    answer_correctness.score +
    context_relevancy.score +
    context_recall.score
) / 3
```

**Example Calculation:**

```
Test Case: "What is Jon Mor's phone number?"

├─ A. Answer Correctness: 1.0  (✅ Correct answer)
├─ B. Context Relevancy:  1.0  (✅ Relevant chunks)
├─ C. Context Recall:     0.5  (⚠️ Partial recall)
└─────────────────────────────
   Final Score: (1.0 + 1.0 + 0.5) / 3 = 0.83
```

**Why Average All Three?**
- ✅ Captures **multiple dimensions** of quality
- ✅ A system can have correct answers (Metric A) but poor retrieval (Metric C)
- ✅ Forces the system to perform well across **all aspects**
- ✅ Prevents "gaming" the evaluation by optimizing only one metric

---

### **Step 7: Save Results**

Results are saved to `evaluation_results.json`:

```json
{
  "question_id": "q1",
  "question": "What is Jon Mor's phone number?",
  "question_type": "needle",
  "ground_truth": "555-1234",
  "system_answer": "555-1234",
  "route": "NEEDLE",
  "retrieved_chunks": ["chunk_id_1"],
  "confidence": 0.95,
  
  "answer_correctness": {
    "score": 1.0,
    "explanation": "System answer matches ground truth exactly."
  },
  "context_relevancy": {
    "score": 1.0,
    "explanation": "All retrieved chunks are relevant to the question."
  },
  "context_recall": {
    "score": 0.5,
    "explanation": "Retrieved chunk_id_1 but missed chunk_id_2."
  },
  
  "final_score": 0.83
}
```

---

## 🎯 **Key Design Principles**

### **1. Independent Judge (No Bias)**

```
┌─────────────────────────────────────┐
│ RAG System: OpenAI (gpt-4o-mini)    │
│            ↓ Different Models ↓     │
│ Judge:      Gemini (gemini-2.5-flash)│
└─────────────────────────────────────┘
          ↑ Unbiased Evaluation
```

**Why This Matters:**
- ❌ **BAD**: Using OpenAI to judge OpenAI → Biased, "marking own homework"
- ✅ **GOOD**: Using Gemini to judge OpenAI → Independent, unbiased perspective

---

### **2. Read-Only Evaluation**

```
┌─────────────────────────────────────┐
│ Evaluation is EXTERNAL              │
├─────────────────────────────────────┤
│ ✅ Does NOT modify RAG system        │
│ ✅ Does NOT affect live answers      │
│ ✅ Offline evaluation post-factum    │
│ ✅ Safe to run anytime               │
└─────────────────────────────────────┘
```

**What This Means:**
- ✅ You can run evaluation **without breaking anything**
- ✅ Evaluation **doesn't change** your system's behavior
- ✅ It's purely **observational** and **analytical**

---

### **3. Strict JSON Responses**

The judge **MUST** return valid JSON in this exact format:

```json
{
  "score": 1.0,  // Must be 0.0, 0.5, or 1.0
  "explanation": "Brief 2-3 sentence explanation"
}
```

**Why This Matters:**
- ✅ **Structured output** → Easy to parse and analyze
- ✅ **No free-form text** → Prevents judge from going off-topic
- ✅ **Consistent format** → Reliable automation
- ✅ **Type safety** → Scores are always numbers

---

### **4. Conservative Scoring**

The judge is instructed to be **strict** and **conservative**:

```
✅ Penalizes weak matches
✅ Requires explicit evidence
✅ No external knowledge allowed
✅ No generous assumptions
✅ Must see facts explicitly stated
```

**Why This Matters:**
- ✅ **High standards** → Ensures quality
- ✅ **Prevents false positives** → Don't reward lucky guesses
- ✅ **Reproducible** → Same input → Same score
- ✅ **Trustworthy** → Results reflect true quality

---

## 📊 **Complete Evaluation Flow Example**

Let's walk through a **complete example** step-by-step:

### **Test Case:**
```json
{
  "id": "q1",
  "question": "What is Jon Mor's phone number?",
  "ground_truth": "555-1234",
  "expected_chunks": ["chunk_1", "chunk_2"]
}
```

---

### **Step 1: RAG System Runs**

```python
result = orchestrator.run("What is Jon Mor's phone number?")

# Returns:
{
  "answer": "555-1234",
  "route": "NEEDLE",
  "sources": ["chunk_1"],
  "confidence": 0.95,
  "retrieved_chunks_content": ["Jon Mor, phone: 555-1234"]
}
```

---

### **Step 2: Gemini Judge Evaluates**

#### **Metric A: Answer Correctness**

```
Input:
  Question: "What is Jon Mor's phone number?"
  Ground Truth: "555-1234"
  System Answer: "555-1234"

Judge Analysis:
  ✅ System answer matches ground truth exactly
  ✅ No missing information
  ✅ No hallucinations

Output:
  Score: 1.0 ✅
  Explanation: "System answer matches ground truth exactly."
```

---

#### **Metric B: Context Relevancy**

```
Input:
  Question: "What is Jon Mor's phone number?"
  Question Type: "needle"
  Retrieved Chunks:
    - "Jon Mor, phone: 555-1234"

Judge Analysis:
  ✅ Chunk contains phone number information
  ✅ Directly relevant to question
  ✅ No irrelevant information

Output:
  Score: 1.0 ✅
  Explanation: "Chunk contains exactly the information needed."
```

---

#### **Metric C: Context Recall**

```
Input:
  Question: "What is Jon Mor's phone number?"
  Expected Chunks: ["chunk_1", "chunk_2"]
  Retrieved Chunks: ["chunk_1"]

Judge Analysis:
  ✅ Retrieved chunk_1 (expected)
  ❌ Did NOT retrieve chunk_2 (expected)
  ⚠️ Partial recall

Output:
  Score: 0.5 ⚠️
  Explanation: "Retrieved chunk_1 but missed chunk_2."
```

---

### **Step 3: Final Score Computation**

```
Final Score = (A + B + C) / 3
            = (1.0 + 1.0 + 0.5) / 3
            = 0.83
```

---

### **Step 4: Results Summary**

```
╔═══════════════════════════════════════════════╗
║  Test Case q1 Results                         ║
╠═══════════════════════════════════════════════╣
║  Question: "What is Jon Mor's phone number?"  ║
║  Route: NEEDLE                                ║
║                                               ║
║  A. Answer Correctness:  1.0 ✅               ║
║     "Exact match with ground truth"           ║
║                                               ║
║  B. Context Relevancy:   1.0 ✅               ║
║     "All chunks relevant"                     ║
║                                               ║
║  C. Context Recall:      0.5 ⚠️               ║
║     "Partial recall, missed chunk_2"          ║
║                                               ║
║  Final Score:            0.83                 ║
╚═══════════════════════════════════════════════╝
```

---

## 🚀 **How to Run Evaluation**

### **Command:**

```bash
cd evaluation
python run_evaluation.py
```

### **What Happens:**

```
[1/7] Loading test cases...
✅ Loaded 8 test cases

[2/7] Initializing RAG system...
✅ RAG system ready

[3/7] Running test cases through RAG system...
  [1/8] q1: What is Jon Mor's phone number?
    Route: NEEDLE
    Answer: 555-1234...
✅ Collected 8 RAG outputs

[4/7] Initializing Gemini judge...
✅ Judge initialized

[5/7] Running evaluation...
  Evaluating q1...
  Evaluating q2...
  ...
✅ Evaluation complete

[6/7] Displaying results...
📊 EVALUATION RESULTS
q1: What is Jon Mor's phone number?
  A. Answer Correctness: 1.0
  B. Context Relevancy:  1.0
  C. Context Recall:     0.5
  Final Score:           0.83

📈 AVERAGE SCORES
  A. Answer Correctness: 0.88
  B. Context Relevancy:  0.91
  C. Context Recall:     0.75
  Final Score:           0.85

[7/7] Saving results...
✅ Results saved to: evaluation_results.json
```

---

## 📁 **Files Involved**

| File | Purpose |
|------|---------|
| `run_evaluation.py` | Main script - orchestrates entire evaluation |
| `evaluator.py` | Core evaluation logic and Gemini judge |
| `judge_prompts.py` | Prompt templates for each metric |
| `test_cases.json` | Test questions + ground truth answers |
| `evaluation_results.json` | Output - evaluation results |

---

## 🎓 **Understanding the Metrics**

### **Why 3 Separate Metrics?**

```
┌──────────────────────────────────────────────┐
│ Metric A: Answer Correctness                │
│   → Measures: "Did we get the right answer?"│
│   → Focus: End result quality                │
└──────────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────────┐
│ Metric B: Context Relevancy                  │
│   → Measures: "Did we use relevant chunks?"  │
│   → Focus: Retrieval quality                 │
└──────────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────────┐
│ Metric C: Context Recall                     │
│   → Measures: "Did we find expected chunks?" │
│   → Focus: Retrieval completeness            │
└──────────────────────────────────────────────┘
```

**Each metric catches different failures:**

| Scenario | A | B | C | Problem Detected |
|----------|---|---|---|------------------|
| Perfect system | 1.0 | 1.0 | 1.0 | ✅ Everything works |
| Lucky guess | 1.0 | 0.0 | 0.0 | ⚠️ Right answer, wrong chunks |
| Good retrieval, bad synthesis | 0.0 | 1.0 | 1.0 | ⚠️ Got chunks, wrong answer |
| Incomplete retrieval | 0.5 | 0.5 | 0.5 | ⚠️ Partial everything |
| Completely broken | 0.0 | 0.0 | 0.0 | ❌ Nothing works |

---

## 💡 **Key Insights**

### **1. Why Independent Model Matters**

**Bad Example (Biased):**
```
System: "What is X?"
OpenAI: "X is Y"

Judge (also OpenAI): "This sounds like something I would say! ✅"
→ BIASED evaluation
```

**Good Example (Unbiased):**
```
System: "What is X?"
OpenAI: "X is Y"

Judge (Gemini): "Let me check if this matches ground truth..."
→ INDEPENDENT evaluation
```

---

### **2. Why Conservative Scoring Matters**

**Without Conservative Scoring:**
```
Ground Truth: "555-1234"
System Answer: "5551234" (missing dash)

Lenient Judge: "Close enough! Score: 1.0"
→ HIDES formatting issues
```

**With Conservative Scoring:**
```
Ground Truth: "555-1234"
System Answer: "5551234" (missing dash)

Strict Judge: "Not exact match. Score: 0.5"
→ CATCHES formatting issues
```

---

### **3. Why Read-Only Matters**

```
✅ GOOD: Evaluation observes system externally
   → Safe, reproducible, doesn't break anything

❌ BAD: Evaluation modifies system
   → Dangerous, unreliable, could break production
```

---

## ✅ **Summary**

**LLM-as-a-Judge** is:
- ✅ An **independent AI** (Gemini) evaluating your RAG system
- ✅ **Automated** - no manual checking needed
- ✅ **Consistent** - same inputs → same scores
- ✅ **Unbiased** - uses different model than your system
- ✅ **Multi-dimensional** - evaluates 3 aspects of quality
- ✅ **Scalable** - can evaluate 100+ test cases
- ✅ **Actionable** - provides explanations for debugging

**It works by:**
1. Running test questions through your RAG system
2. Collecting answers and retrieved chunks
3. Asking Gemini to score 3 metrics (0.0, 0.5, 1.0)
4. Computing final score as average
5. Providing detailed explanations

**Why it's powerful:**
- 🎯 Catches issues regular testing might miss
- 🎯 Measures not just correctness, but also **how** you got the answer
- 🎯 Independent perspective prevents overfitting to your model's style
- 🎯 Actionable feedback helps you improve specific components

---

## 🎓 **Analogy**

Think of it like a school exam:

```
┌─────────────────────────────────────────────┐
│ Your RAG System = Student                   │
├─────────────────────────────────────────────┤
│ Test Cases = Exam Questions                 │
├─────────────────────────────────────────────┤
│ Gemini Judge = Teacher (different school)   │
├─────────────────────────────────────────────┤
│ Metrics = Grading Rubric                    │
│   A. Answer Correctness = Did you answer?   │
│   B. Context Relevancy  = Did you cite?     │
│   C. Context Recall     = All sources used? │
└─────────────────────────────────────────────┘
```

**The teacher (Gemini):**
- ❌ Didn't train the student (no bias)
- ✅ Grades based on rubric (consistent)
- ✅ Checks work, not just answer (comprehensive)
- ✅ Provides feedback (actionable)

---

## 📚 **Further Reading**

- `run_evaluation.py` - Main evaluation script
- `evaluator.py` - Core evaluation logic
- `judge_prompts.py` - Detailed prompt templates
- `test_cases.json` - Example test cases
- `evaluation_results.json` - Sample output

---

**Built for RagAgentv2 - Auto Claims RAG System** 🚗

evaluation/evaluation_explained.md
├─ 📊 What is LLM-as-a-Judge?
├─ 🎯 The Big Picture (Visual Flow)
├─ 🔄 7-Step Evaluation Pipeline
│   ├─ Step 1: Load Test Cases
│   ├─ Step 2: Run Through RAG System
│   ├─ Step 3: Collect Results
│   ├─ Step 4: Initialize Gemini Judge
│   ├─ Step 5: Evaluate 3 Metrics
│   │   ├─ Metric A: Answer Correctness
│   │   ├─ Metric B: Context Relevancy
│   │   └─ Metric C: Context Recall
│   ├─ Step 6: Aggregate Scores
│   └─ Step 7: Save Results
├─ 🎯 Key Design Principles
├─ 📊 Complete Evaluation Flow Example
├─ 🚀 How to Run Evaluation
├─ 📁 Files Involved
├─ 🎓 Understanding the Metrics
├─ 💡 Key Insights
├─ ✅ Summary
└─ 🎓 School Exam Analogy