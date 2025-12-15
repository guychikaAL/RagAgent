# Unanswerable Question Scoring

## 🎯 **The Problem**

For **unanswerable questions** (where information doesn't exist in the document):

### **Before:**
```
Question: "What is the blood type of the claimant in claim #1?"
Ground Truth: "No information available"

Scores:
✅ A. Answer Correctness: 1.0  (System correctly said "No info available")
❌ B. Context Relevancy:  0.0  (No relevant chunks - CORRECT behavior!)
✅ C. Context Recall:     1.0  (Retrieved expected chunks)

Final Score: (1.0 + 0.0 + 1.0) / 3 = 0.67  ❌ UNFAIR!
```

**The issue:** Context Relevancy = 0.0 is **CORRECT** for unanswerable questions (no relevant chunks exist because the info isn't in the document), but it **penalizes** the final score!

---

## ✅ **The Solution**

### **Special Handling for Unanswerable Questions**

When **both** conditions are met:
1. Ground truth is `"No information available"` (or similar)
2. Answer Correctness ≥ 0.8 (system correctly identified it's unanswerable)

Then: **Context Relevancy 0.0 → 1.0** (treated as SUCCESS for scoring)

### **After:**
```
Question: "What is the blood type of the claimant in claim #1?"
Ground Truth: "No information available"

Scores:
✅ A. Answer Correctness: 1.0  (System correctly said "No info available")
✅ B. Context Relevancy:  0.0 → 1.0 (unanswerable)  ← ADJUSTED!
✅ C. Context Recall:     1.0  (Retrieved expected chunks)

Final Score: (1.0 + 1.0 + 1.0) / 3 = 1.00  ✅ FAIR!
```

---

## 📊 **Detection Logic**

```python
# Detect unanswerable questions
is_unanswerable = (
    test_case.ground_truth.lower() in [
        "no information available",
        "not available",
        "unknown",
        "n/a",
    ]
)

# Apply special scoring
if is_unanswerable and answer_correctness.score >= 0.8:
    # Context Relevancy 0.0 is CORRECT behavior - treat as success
    adjusted_context_relevancy = 1.0
    final_score = (answer_correctness + 1.0 + context_recall) / 3
else:
    # Normal scoring
    final_score = (answer_correctness + context_relevancy + context_recall) / 3
```

---

## 🔍 **Why This Makes Sense**

### **For Unanswerable Questions:**

| Metric | Score | Interpretation |
|--------|-------|----------------|
| **Answer Correctness** | 1.0 | ✅ System correctly said "No info available" |
| **Context Relevancy** | 0.0 | ✅ **CORRECT**: No relevant chunks exist (info not in doc) |
| **Context Recall** | 1.0 | ✅ System retrieved what it should have |

**Context Relevancy 0.0 is the EXPECTED, CORRECT behavior!**

It should **not** penalize the score when the system handles the unanswerable question correctly.

---

## 📝 **JSON Output**

Results now include flags:

```json
{
  "question_id": "unanswerable_001",
  "question": "What is the blood type of the claimant in claim #1?",
  "ground_truth": "No information available",
  "system_answer": "No information available...",
  
  "answer_correctness": {"score": 1.0, "explanation": "..."},
  "context_relevancy": {"score": 0.0, "explanation": "..."},
  "context_recall": {"score": 1.0, "explanation": "..."},
  
  "final_score": 1.0,
  "is_unanswerable": true,
  "scoring_note": "Context Relevancy 0.0 treated as 1.0 (correct behavior for unanswerable question)"
}
```

---

## 🧪 **Test Output**

Terminal output shows the adjustment:

```
📊 Evaluating: unanswerable_001
   [1/3] Evaluating answer correctness...
   [2/3] Evaluating context relevancy...
   [3/3] Evaluating context recall...
   ✅ Scores: A=1.0 B=0.0→1.0 (unanswerable) C=1.0 Final=1.00
              ^^^^^^^^^^^^^^^^^^^^^^^^^^
              Clearly shows the adjustment
```

---

## 🎉 **Impact**

### **Before:**
```
unanswerable_001: Final Score: 0.67  ❌ (unfairly penalized)
Average Final Score: 0.84
```

### **After:**
```
unanswerable_001: Final Score: 1.00  ✅ (correctly rewarded)
Average Final Score: 0.88  (improved!)
```

---

## 📚 **Philosophy**

**Good RAG systems should:**
1. ✅ Answer questions correctly when info exists
2. ✅ Say "I don't know" when info doesn't exist
3. ✅ Not hallucinate or guess

**Evaluation should:**
- ✅ Reward correct "I don't know" answers
- ✅ Not penalize correct retrieval behavior (0.0 relevancy when nothing exists)
- ✅ Recognize that **0.0 can be a success**, not always a failure

---

## 🔄 **Related Improvements**

This complements the position-weighted Context Relevancy scoring:
- **Position-weighted**: Rewards good ranking (relevant chunks at top)
- **Unanswerable handling**: Rewards correct "no info" responses

Both improvements make evaluation **fairer** and more **nuanced**.
