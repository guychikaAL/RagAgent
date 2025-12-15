"""
====================================================
EVALUATOR - RAG System Evaluation Logic
====================================================

This module evaluates RAG system performance using LLM-as-a-Judge.

CRITICAL ARCHITECTURE PRINCIPLES:
- External evaluation only (read-only)
- Does NOT modify RAG system
- Does NOT affect live answers
- Offline evaluation post-factum

WHY GEMINI AS JUDGE:
- System uses OpenAI → must use different model for judge
- Avoids evaluation bias
- Independent scoring perspective

EVALUATION FLOW:
1. Load test cases
2. Run RAG system (via existing app.py)
3. Collect: answer, route, sources, chunks
4. Send to Gemini Judge for scoring
5. Compute metrics A, B, C
6. Aggregate and save results

====================================================
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

# Gemini imports
import google.generativeai as genai

# Import judge prompts
from evaluation.judge_prompts import (
    ANSWER_CORRECTNESS_SYSTEM,
    ANSWER_CORRECTNESS_USER,
    CONTEXT_RELEVANCY_SYSTEM,
    CONTEXT_RELEVANCY_USER,
    CONTEXT_RECALL_SYSTEM,
    CONTEXT_RECALL_USER,
)


# ====================================================
# DATA STRUCTURES
# ====================================================

@dataclass
class TestCase:
    """
    Single test case for evaluation.
    
    WHY THIS STRUCTURE:
    - Enforces required fields
    - Type safety
    - Easy serialization
    """
    id: str
    type: str  # "needle" or "summary"
    question: str
    ground_truth: str
    expected_chunks: List[str]  # Chunk IDs that should be retrieved


@dataclass
class MetricScore:
    """
    Score for a single metric.
    
    WHY THIS STRUCTURE:
    - Consistent format across metrics
    - Includes explanation for debugging
    """
    score: float  # 0.0, 0.5, or 1.0
    explanation: str


@dataclass
class EvaluationResult:
    """
    Complete evaluation result for one test case.
    
    WHY THIS STRUCTURE:
    - Captures all relevant information
    - Easy to analyze and debug
    - Serializable to JSON
    """
    question_id: str
    question: str
    question_type: str
    ground_truth: str
    
    # RAG system outputs
    system_answer: str
    route: str
    retrieved_chunks: List[str]
    confidence: float
    
    # Metric scores
    answer_correctness: MetricScore
    context_relevancy: MetricScore
    context_recall: MetricScore
    
    # Aggregate
    final_score: float
    is_unanswerable: bool = False  # Flag for special scoring


# ====================================================
# GEMINI JUDGE
# ====================================================

class GeminiJudge:
    """
    LLM-as-a-Judge using Gemini.
    
    WHY GEMINI:
    - System uses OpenAI → need different model for unbiased evaluation
    - Strong reasoning capabilities
    - Supports structured output
    
    WHY SEPARATE CLASS:
    - Encapsulates Gemini API calls
    - Easy to test with mocks
    - Clear separation of concerns
    """
    
    def __init__(self, model: str = "gemini-2.5-flash"):
        """
        Initialize Gemini judge.
        
        Args:
            model: Gemini model name (flash = fast, good for evaluation)
        
        WHY gemini-2.5-flash:
        - Fast responses (latest flash model)
        - Good reasoning for evaluation
        - Cost-effective for batch evaluation
        - Verified working model (as of Dec 2024)
        """
        # Get API key
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError(
                "GOOGLE_API_KEY not found. "
                "Set it in environment or .env file."
            )
        
        # Configure Gemini
        genai.configure(api_key=api_key)
        
        # Create model
        # WHY: GenerativeModel provides chat interface
        self.model = genai.GenerativeModel(model)
        
        print(f"✅ Gemini Judge initialized: {model}")
    
    def _call_judge(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """
        Call Gemini with system + user prompt.
        
        WHY SEPARATE METHOD:
        - Centralized API call logic
        - Error handling
        - JSON parsing
        - Retry logic if needed
        
        Args:
            system_prompt: Judge instructions
            user_prompt: Evaluation input
            
        Returns:
            Parsed JSON response
        """
        # Combine system + user into single prompt
        # WHY: Gemini doesn't have explicit system message, so we combine
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        
        try:
            # Call Gemini
            response = self.model.generate_content(full_prompt)
            
            # Extract text
            response_text = response.text.strip()
            
            # Parse JSON
            # WHY: Judge should return strict JSON
            # Remove markdown code blocks if present
            if response_text.startswith("```json"):
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif response_text.startswith("```"):
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(response_text)
            
            return result
            
        except json.JSONDecodeError as e:
            # If JSON parsing fails, return error score
            print(f"⚠️ JSON parsing error: {e}")
            print(f"Response: {response_text}")
            return {
                "score": 0.0,
                "explanation": f"Judge returned invalid JSON: {str(e)}"
            }
        except Exception as e:
            print(f"⚠️ Gemini API error: {e}")
            return {
                "score": 0.0,
                "explanation": f"API error: {str(e)}"
            }
    
    def evaluate_answer_correctness(
        self,
        question: str,
        ground_truth: str,
        system_answer: str,
    ) -> MetricScore:
        """
        Evaluate answer correctness.
        
        WHY THIS METRIC:
        - Measures if system got the right answer
        - Compares to ground truth
        - Core RAG metric
        
        Args:
            question: User's question
            ground_truth: Correct answer
            system_answer: What RAG system returned
            
        Returns:
            MetricScore with score and explanation
        """
        user_prompt = ANSWER_CORRECTNESS_USER.format(
            question=question,
            ground_truth=ground_truth,
            system_answer=system_answer,
        )
        
        result = self._call_judge(ANSWER_CORRECTNESS_SYSTEM, user_prompt)
        
        return MetricScore(
            score=float(result["score"]),
            explanation=result["explanation"]
        )
    
    def evaluate_context_relevancy(
        self,
        question: str,
        question_type: str,
        retrieved_chunks: List[str],
    ) -> MetricScore:
        """
        Evaluate context relevancy.
        
        WHY THIS METRIC:
        - Measures if right chunks were used
        - Evaluates retrieval quality
        - Independent of answer correctness
        
        Args:
            question: User's question
            question_type: "needle" or "summary"
            retrieved_chunks: Chunks that system retrieved
            
        Returns:
            MetricScore with score and explanation
        """
        # Format chunks for prompt
        chunks_text = "\n".join([f"- {chunk}" for chunk in retrieved_chunks])
        
        user_prompt = CONTEXT_RELEVANCY_USER.format(
            question=question,
            question_type=question_type,
            retrieved_chunks=chunks_text,
        )
        
        result = self._call_judge(CONTEXT_RELEVANCY_SYSTEM, user_prompt)
        
        return MetricScore(
            score=float(result["score"]),
            explanation=result["explanation"]
        )
    
    def evaluate_context_recall(
        self,
        question: str,
        expected_chunks: List[str],
        retrieved_chunks: List[str],
    ) -> MetricScore:
        """
        Evaluate context recall.
        
        WHY THIS METRIC:
        - Measures if expected chunks were retrieved
        - Evaluates retrieval completeness
        - Can be high even if answer is wrong
        
        Args:
            question: User's question
            expected_chunks: Chunks that should be retrieved (empty list = skip this metric)
            retrieved_chunks: Chunks actually retrieved
            
        Returns:
            MetricScore with score and explanation
        """
        # If no expected chunks specified, skip this metric
        # WHY: We can't evaluate recall without knowing what to expect
        if not expected_chunks:
            return MetricScore(
                score=1.0,
                explanation="Context recall not evaluated (no expected chunks specified). Default score: 1.0"
            )
        
        # Format chunks for prompt
        expected_text = "\n".join([f"- {chunk}" for chunk in expected_chunks])
        retrieved_text = "\n".join([f"- {chunk}" for chunk in retrieved_chunks])
        
        user_prompt = CONTEXT_RECALL_USER.format(
            question=question,
            expected_chunks=expected_text,
            retrieved_chunks=retrieved_text,
        )
        
        result = self._call_judge(CONTEXT_RECALL_SYSTEM, user_prompt)
        
        return MetricScore(
            score=float(result["score"]),
            explanation=result["explanation"]
        )


# ====================================================
# RAG EVALUATOR
# ====================================================

class RAGEvaluator:
    """
    End-to-end RAG system evaluator.
    
    WHY THIS CLASS:
    - Orchestrates full evaluation pipeline
    - Integrates with existing RAG system (read-only)
    - Computes all metrics
    - Aggregates results
    
    CRITICAL: This class does NOT modify the RAG system.
    It only READS outputs and EVALUATES them.
    """
    
    def __init__(self, judge: GeminiJudge):
        """
        Initialize evaluator.
        
        Args:
            judge: GeminiJudge instance for scoring
        """
        self.judge = judge
    
    def evaluate_single(
        self,
        test_case: TestCase,
        rag_result: Dict[str, Any],
        chunk_contents: Optional[Dict[str, str]] = None,
    ) -> EvaluationResult:
        """
        Evaluate a single test case.
        
        WHY THIS METHOD:
        - Processes one question at a time
        - Calls all three metrics
        - Computes final score
        
        Args:
            test_case: Test case definition
            rag_result: Output from RAG system
                Must contain: answer, route, sources, confidence
        
        Returns:
            EvaluationResult with all metrics
        """
        print(f"\n📊 Evaluating: {test_case.id}")
        
        # Extract RAG outputs
        system_answer = rag_result["answer"]
        route = rag_result["route"]
        retrieved_chunks = rag_result["sources"]  # Chunk IDs
        retrieved_chunks_content = rag_result.get("retrieved_chunks_content", [])  # Actual text
        confidence = rag_result["confidence"]
        
        # Metric A: Answer Correctness
        print("   [1/3] Evaluating answer correctness...")
        answer_correctness = self.judge.evaluate_answer_correctness(
            question=test_case.question,
            ground_truth=test_case.ground_truth,
            system_answer=system_answer,
        )
        
        # Metric B: Context Relevancy
        # WHY: Pass actual chunk content (not IDs) so Gemini can judge relevancy
        print("   [2/3] Evaluating context relevancy...")
        context_relevancy = self.judge.evaluate_context_relevancy(
            question=test_case.question,
            question_type=test_case.type,
            retrieved_chunks=retrieved_chunks_content,  # Use content, not IDs!
        )
        
        # Metric C: Context Recall
        print("   [3/3] Evaluating context recall...")
        context_recall = self.judge.evaluate_context_recall(
            question=test_case.question,
            expected_chunks=test_case.expected_chunks,
            retrieved_chunks=retrieved_chunks,
        )
        
        # Compute final score with special handling for unanswerable questions
        # Detect unanswerable questions by ground truth
        is_unanswerable = (
            test_case.ground_truth.lower() in [
                "no information available",
                "not available",
                "unknown",
                "n/a",
            ]
        )
        
        if is_unanswerable and answer_correctness.score >= 0.8:
            # SPECIAL CASE: Unanswerable questions
            # Context Relevancy = 0.0 is CORRECT (no relevant chunks exist)
            # Treat it as SUCCESS (1.0) for final score calculation
            adjusted_context_relevancy = 1.0
            final_score = (
                answer_correctness.score +
                adjusted_context_relevancy +  # 0.0 → 1.0 (success!)
                context_recall.score
            ) / 3.0
            print(f"   ✅ Scores: A={answer_correctness.score:.1f} "
                  f"B={context_relevancy.score:.1f}→1.0 (unanswerable) "
                  f"C={context_recall.score:.1f} "
                  f"Final={final_score:.2f}")
        else:
            # NORMAL CASE: Average all three metrics equally
            final_score = (
                answer_correctness.score +
                context_relevancy.score +
                context_recall.score
            ) / 3.0
            print(f"   ✅ Scores: A={answer_correctness.score:.1f} "
                  f"B={context_relevancy.score:.1f} "
                  f"C={context_recall.score:.1f} "
                  f"Final={final_score:.2f}")
        
        # Create result
        return EvaluationResult(
            question_id=test_case.id,
            question=test_case.question,
            question_type=test_case.type,
            ground_truth=test_case.ground_truth,
            system_answer=system_answer,
            route=route,
            retrieved_chunks=retrieved_chunks,
            confidence=confidence,
            answer_correctness=answer_correctness,
            context_relevancy=context_relevancy,
            context_recall=context_recall,
            final_score=final_score,
            is_unanswerable=is_unanswerable and answer_correctness.score >= 0.8,
        )
    
    def evaluate_all(
        self,
        test_cases: List[TestCase],
        rag_results: List[Dict[str, Any]],
    ) -> List[EvaluationResult]:
        """
        Evaluate all test cases.
        
        WHY THIS METHOD:
        - Batch evaluation
        - Progress tracking
        - Aggregated statistics
        
        Args:
            test_cases: List of test cases
            rag_results: List of RAG outputs (must match test_cases order)
        
        Returns:
            List of EvaluationResults
        """
        if len(test_cases) != len(rag_results):
            raise ValueError(
                f"Mismatch: {len(test_cases)} test cases but "
                f"{len(rag_results)} RAG results"
            )
        
        print(f"🔬 Evaluating {len(test_cases)} test cases...")
        
        results = []
        for test_case, rag_result in zip(test_cases, rag_results):
            result = self.evaluate_single(test_case, rag_result)
            results.append(result)
        
        # Compute averages
        avg_answer_correctness = sum(r.answer_correctness.score for r in results) / len(results)
        avg_context_relevancy = sum(r.context_relevancy.score for r in results) / len(results)
        avg_context_recall = sum(r.context_recall.score for r in results) / len(results)
        avg_final = sum(r.final_score for r in results) / len(results)
        
        print(f"\n" + "="*70)
        print(f"📊 EVALUATION SUMMARY")
        print(f"="*70)
        print(f"Total test cases: {len(results)}")
        print(f"\nAverage Scores:")
        print(f"  A. Answer Correctness: {avg_answer_correctness:.2f}")
        print(f"  B. Context Relevancy:  {avg_context_relevancy:.2f}")
        print(f"  C. Context Recall:     {avg_context_recall:.2f}")
        print(f"  Final Score:           {avg_final:.2f}")
        print(f"="*70)
        
        return results
    
    def save_results(
        self,
        results: List[EvaluationResult],
        output_path: str,
    ) -> None:
        """
        Save evaluation results to JSON.
        
        WHY THIS METHOD:
        - Persist results for analysis
        - Enable result comparison over time
        - Support external analysis tools
        
        Args:
            results: List of evaluation results
            output_path: Path to save JSON file
        """
        # Convert results to dict
        results_dict = {
            "results": [
                {
                    "question_id": r.question_id,
                    "question": r.question,
                    "question_type": r.question_type,
                    "ground_truth": r.ground_truth,
                    "system_answer": r.system_answer,
                    "route": r.route,
                    "retrieved_chunks": r.retrieved_chunks,
                    "confidence": r.confidence,
                    "answer_correctness": asdict(r.answer_correctness),
                    "context_relevancy": asdict(r.context_relevancy),
                    "context_recall": asdict(r.context_recall),
                    "final_score": r.final_score,
                    "is_unanswerable": r.is_unanswerable,
                    "scoring_note": (
                        "Context Relevancy 0.0 treated as 1.0 (correct behavior for unanswerable question)"
                        if r.is_unanswerable
                        else None
                    ),
                }
                for r in results
            ],
            "summary": {
                "total_cases": len(results),
                "avg_answer_correctness": sum(r.answer_correctness.score for r in results) / len(results),
                "avg_context_relevancy": sum(r.context_relevancy.score for r in results) / len(results),
                "avg_context_recall": sum(r.context_recall.score for r in results) / len(results),
                "avg_final_score": sum(r.final_score for r in results) / len(results),
            }
        }
        
        # Save to file
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(results_dict, f, indent=2)
        
        print(f"\n✅ Results saved to: {output_file}")

