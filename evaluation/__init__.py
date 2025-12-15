"""
====================================================
EVALUATION LAYER
====================================================

External, offline evaluation for the RAG system using LLM-as-a-Judge.

WHY THIS EXISTS:
- Measure system performance objectively
- Track improvements over time
- Identify failure modes
- Validate system changes

CRITICAL PRINCIPLES:
- Read-only access to RAG system
- Never affects live answers
- Uses Gemini (not OpenAI) as judge
- Completely isolated from production

METRICS:
A. Answer Correctness - Does answer match ground truth?
B. Context Relevancy - Did agent use relevant chunks?
C. Context Recall - Were expected chunks retrieved?

====================================================
"""

from evaluation.evaluator import (
    GeminiJudge,
    RAGEvaluator,
    TestCase,
    MetricScore,
    EvaluationResult,
)

__all__ = [
    "GeminiJudge",
    "RAGEvaluator",
    "TestCase",
    "MetricScore",
    "EvaluationResult",
]

