"""
====================================================
RAGAS METRICS - Metric Definitions
====================================================

This module defines which RAGAS metrics are used
for secondary evaluation.

METRICS USED:
- context_recall: Measures if ground truth can be attributed to contexts
- context_precision: Measures if relevant contexts are ranked higher
- faithfulness: Measures if answer is grounded in contexts
- answer_relevancy: Measures if answer addresses the question

WHY THESE METRICS:
- Standard RAGAS metrics for RAG evaluation
- Complement custom LLM-as-a-Judge
- Focus on retrieval quality and faithfulness

CRITICAL:
- These metrics are for OFFLINE ANALYSIS ONLY
- NOT used during inference
- NOT fed back into system
====================================================
"""

try:
    from ragas.metrics import (
        context_recall,
        context_precision,
        faithfulness,
        answer_relevancy,
    )
except ImportError:
    raise ImportError(
        "RAGAS not installed. Please run: pip install ragas"
    )

# Define metrics to evaluate
RAGAS_METRICS = [
    context_recall,
    context_precision,
    faithfulness,
    answer_relevancy,
]

# Metric names for reporting
METRIC_NAMES = [
    "context_recall",
    "context_precision",
    "faithfulness",
    "answer_relevancy",
]
