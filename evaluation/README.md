# 🔬 Evaluation Layer

## Overview

This directory contains the evaluation framework for the RAG system using **LLM-as-a-Judge** methodology.

### Critical Principle: External Evaluation

The evaluation layer is **completely isolated** from the RAG system:
- ✅ **Read-only** access to RAG outputs
- ✅ **Offline** evaluation (post-factum)
- ✅ **Non-invasive** (never affects live answers)
- ✅ **Independent** judge model (Gemini, not OpenAI)

---

## Evaluation Methodology

### Model Separation (MANDATORY)

| Component | Model | Why |
|-----------|-------|-----|
| **RAG System** | OpenAI (gpt-4o-mini) | Production system |
| **Judge** | Gemini (gemini-1.5-flash) | Evaluation only |

**Why different models?**
- Avoid evaluation bias
- Independent scoring perspective
- Gemini won't favor OpenAI's outputs

---

## Three Metrics

### A. Answer Correctness

**What**: Does the system answer match the ground truth?

**Scoring**:
- `1.0` = Fully correct (all facts match)
- `0.5` = Partially correct (some facts match)
- `0.0` = Incorrect (wrong or hallucinated)

**Example**:
```
Question: "What is Jon Mor's phone number?"
Ground Truth: "(555) 100-2000"
System Answer: "(555) 100-2000"
Score: 1.0 ✅
```

### B. Context Relevancy

**What**: Did the agent use the MOST relevant chunks?

**Evaluates**:
- Are retrieved chunks semantically related to the question?
- For needle questions: atomic child chunks?
- For summary questions: merged parent chunks?

**Scoring**:
- `1.0` = All chunks highly relevant
- `0.5` = Some relevant, some not
- `0.0` = Chunks not relevant to question

**Example**:
```
Question: "What is Jon Mor's phone number?"
Retrieved: ["claimant_contact_info_claim_1"]
Score: 1.0 ✅ (correct chunk type for needle question)
```

### C. Context Recall

**What**: Were the expected chunks retrieved?

**Evaluates**:
- Did retrieval find the chunks that SHOULD be found?
- Independent of answer quality
- Can be high even if answer is wrong

**Scoring**:
- `1.0` = All expected chunks retrieved
- `0.5` = Some expected chunks retrieved
- `0.0` = No expected chunks retrieved

**Example**:
```
Expected: ["claimant_info_claim_1", "incident_details_claim_1"]
Retrieved: ["claimant_info_claim_1", "incident_details_claim_1", "vehicle_info_claim_1"]
Score: 1.0 ✅ (all expected chunks present)
```

---

## Files

```
evaluation/
├── judge_prompts.py          # Prompt templates for Gemini
├── evaluator.py              # Core evaluation logic
├── test_cases.json           # Test dataset
├── run_evaluation.ipynb      # Notebook for running evaluation
├── evaluation_results.json   # Output storage
└── README.md                 # This file
```

### 1. `judge_prompts.py`

Contains three prompt templates:
- `ANSWER_CORRECTNESS_SYSTEM` + `ANSWER_CORRECTNESS_USER`
- `CONTEXT_RELEVANCY_SYSTEM` + `CONTEXT_RELEVANCY_USER`
- `CONTEXT_RECALL_SYSTEM` + `CONTEXT_RECALL_USER`

Each prompt:
- Instructs Gemini to be conservative
- Prohibits external knowledge
- Enforces strict JSON output

### 2. `evaluator.py`

Core classes:
- **`GeminiJudge`**: Calls Gemini API for scoring
- **`RAGEvaluator`**: Orchestrates full evaluation pipeline
- **`TestCase`**: Test case data structure
- **`EvaluationResult`**: Result data structure

Pipeline:
1. Load test cases
2. Run RAG system (read-only)
3. Collect outputs
4. Send to Gemini Judge
5. Compute metrics
6. Save results

### 3. `test_cases.json`

Test dataset with:
- 4 needle questions (atomic facts)
- 3 summary questions (comprehensive)
- 1 unanswerable question

Each test case includes:
```json
{
  "id": "needle_001",
  "type": "needle",
  "question": "What is Jon Mor's phone number?",
  "ground_truth": "(555) 100-2000",
  "expected_chunks": ["claimant_contact_info_claim_1"]
}
```

### 4. `run_evaluation.ipynb`

Jupyter notebook for running evaluation:
1. Load test cases
2. Initialize RAG system (read-only)
3. Run questions through RAG
4. Initialize Gemini Judge
5. Evaluate all cases
6. Display results
7. Highlight failures
8. Save to JSON

### 5. `evaluation_results.json`

Output format:
```json
{
  "results": [
    {
      "question_id": "needle_001",
      "answer_correctness": {"score": 1.0, "explanation": "..."},
      "context_relevancy": {"score": 1.0, "explanation": "..."},
      "context_recall": {"score": 1.0, "explanation": "..."},
      "final_score": 1.0
    }
  ],
  "summary": {
    "total_cases": 8,
    "avg_answer_correctness": 0.85,
    "avg_context_relevancy": 0.90,
    "avg_context_recall": 0.88,
    "avg_final_score": 0.88
  }
}
```

---

## Usage

### Prerequisites

1. Set up Gemini API key:
```bash
export GOOGLE_API_KEY="your_gemini_api_key"
```

Or add to `.env`:
```
GOOGLE_API_KEY=your_gemini_api_key
```

2. Ensure RAG system is built:
```bash
python build_production_index.py
```

### Run Evaluation

**Option 1: Jupyter Notebook (Recommended)**
```bash
cd evaluation
jupyter notebook run_evaluation.ipynb
```

**Option 2: Python Script**
```python
from evaluation.evaluator import GeminiJudge, RAGEvaluator, TestCase
import json

# Load test cases
with open("evaluation/test_cases.json") as f:
    test_data = json.load(f)

# Initialize judge
judge = GeminiJudge()
evaluator = RAGEvaluator(judge)

# Run RAG system and evaluate
# ... (see notebook for full code)
```

---

## Known Limitations

### 1. Judge Subjectivity

**Issue**: Gemini's scoring may vary slightly between runs.

**Mitigation**:
- Temperature = 0.0 (most deterministic)
- Strict prompt instructions
- Clear scoring criteria

### 2. Chunk ID Matching

**Issue**: Expected chunk IDs must match actual chunk IDs exactly.

**Mitigation**:
- Use consistent chunk naming convention
- Inspect actual chunk IDs from RAG system
- Update test_cases.json accordingly

### 3. Ground Truth Quality

**Issue**: Ground truth answers must be accurate and comprehensive.

**Mitigation**:
- Manually verify each ground truth
- Include only verifiable facts
- Document any ambiguities

### 4. Context Window Limits

**Issue**: Very long retrieved contexts may exceed Gemini's window.

**Mitigation**:
- Limit chunk text in prompts
- Summarize chunk content if needed
- Use gemini-1.5-flash (longer context window)

### 5. API Costs

**Issue**: Each evaluation calls Gemini 3 times per test case.

**Cost Estimate**:
- 8 test cases × 3 metrics = 24 API calls
- ~$0.01-0.05 per evaluation run
- Batch evaluation recommended

---

## Failure Modes

### Answer Correctness Failures

**Symptom**: `answer_correctness.score < 0.5`

**Possible Causes**:
1. Retrieval failed (wrong chunks)
2. Agent hallucinated
3. Answer incomplete
4. Ground truth incorrect

**Debug**:
- Check `retrieved_chunks` field
- Compare system answer to ground truth
- Verify ground truth accuracy

### Context Relevancy Failures

**Symptom**: `context_relevancy.score < 0.5`

**Possible Causes**:
1. Retrieval returned irrelevant chunks
2. Embedding quality issue
3. Query preprocessing failed
4. Wrong chunk types retrieved

**Debug**:
- Inspect retrieved chunk content
- Check if chunks match question semantically
- Verify chunk types (child vs parent)

### Context Recall Failures

**Symptom**: `context_recall.score < 0.5`

**Possible Causes**:
1. Expected chunks not in index
2. Similarity threshold too high
3. Embedding mismatch
4. Chunk IDs incorrect in test case

**Debug**:
- Verify expected chunks exist in index
- Check actual vs expected chunk IDs
- Lower similarity threshold
- Re-build index if needed

---

## Best Practices

### 1. Iterative Improvement

1. Run evaluation
2. Identify failures
3. Debug root causes
4. Fix RAG system (if needed)
5. Re-run evaluation
6. Track improvements over time

### 2. Version Control

- Version evaluation results by date
- Track metric trends over time
- Compare before/after system changes

### 3. Test Case Maintenance

- Add test cases for edge cases
- Update ground truth when system improves
- Remove obsolete test cases

### 4. Judge Prompt Tuning

- Iterate on judge prompts if scoring seems off
- A/B test different prompt versions
- Document prompt changes

---

## Integration with CI/CD

### Automated Evaluation

```bash
# In CI pipeline
python -m evaluation.run_evaluation
```

### Quality Gates

```python
# Fail build if scores drop below threshold
if avg_final_score < 0.70:
    raise Exception("Evaluation failed: score too low")
```

---

## Future Enhancements

1. **Multi-Judge Consensus**: Use multiple judges (Gemini, Claude, GPT) and average scores
2. **Human Validation**: Compare judge scores to human annotations
3. **A/B Testing**: Compare system versions side-by-side
4. **Retrieval Metrics**: Add precision@k, recall@k, MRR
5. **Latency Tracking**: Measure query response times
6. **Cost Tracking**: Monitor OpenAI API costs per query

---

## References

- [LLM-as-a-Judge Paper](https://arxiv.org/abs/2306.05685)
- [RAG Evaluation Best Practices](https://docs.llamaindex.ai/en/stable/examples/evaluation/)
- [Gemini API Documentation](https://ai.google.dev/docs)

---

## Support

For questions or issues:
1. Check this README
2. Inspect evaluation logs
3. Review test case definitions
4. Verify API keys are set

---

**Last Updated**: December 2024

