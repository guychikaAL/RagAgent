"""
Run RAG System Evaluation

This script runs the full evaluation pipeline using Gemini as judge.

Usage:
    cd evaluation
    python run_evaluation.py
"""

import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Setup paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment
load_dotenv(project_root / ".env")

# Import evaluation components
from evaluation.evaluator import GeminiJudge, RAGEvaluator, TestCase

# Import RAG system (READ-ONLY)
from RAG.Index_Layer.index_layer import ClaimIndexManager
from RAG.Agents import RouterAgent, NeedleAgent, SummaryAgent
from RAG.Orchestration import Orchestrator


def main():
    print("="*70)
    print("🔬 RAG SYSTEM EVALUATION")
    print("="*70)
    
    # Step 1: Load test cases
    print("\n[1/7] Loading test cases...")
    
    # Using FULL test set (paid API has no limits)
    eval_dir = Path(__file__).parent
    test_file = eval_dir / "test_cases.json"  # 8 comprehensive test cases
    
    print(f"   Using: {test_file}")
    with open(test_file, "r") as f:
        test_data = json.load(f)
    
    test_cases = [
        TestCase(
            id=tc["id"],
            type=tc["type"],
            question=tc["question"],
            ground_truth=tc["ground_truth"],
            expected_chunks=tc["expected_chunks"]
        )
        for tc in test_data["test_cases"]
    ]
    
    print(f"✅ Loaded {len(test_cases)} test cases")
    
    # Step 2: Initialize RAG system (READ-ONLY)
    print("\n[2/7] Initializing RAG system (read-only)...")
    
    index_manager = ClaimIndexManager()
    index_manager.load_index(persist_dir=str(project_root / "production_index"))
    
    # Reduced top_k from 5 to 3 for better precision (fewer irrelevant chunks)
    # Increased threshold from 0.7 to 0.75 for higher quality matches
    needle_retriever = index_manager.get_needle_retriever(top_k=3, similarity_threshold=0.75)
    # Reduced top_k from 15 to 10 for MapReduce (fewer irrelevant chunks from other claims)
    map_reduce_query_engine = index_manager.get_map_reduce_query_engine(top_k=10)
    
    router = RouterAgent(model="gpt-4o-mini", temperature=0.0)
    needle = NeedleAgent(model="gpt-4o-mini", temperature=0.0)
    summary = SummaryAgent(model="gpt-4o-mini", temperature=0.2)
    
    orchestrator = Orchestrator(
        router_agent=router,
        needle_agent=needle,
        summary_agent=summary,
        needle_retriever=needle_retriever,
        map_reduce_query_engine=map_reduce_query_engine,
    )
    
    print("✅ RAG system ready")
    
    # Step 3: Run questions through RAG system
    print("\n[3/7] Running test cases through RAG system...")
    
    rag_results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n  [{i}/{len(test_cases)}] {test_case.id}: {test_case.question}")
        
        try:
            # Run RAG system (READ-ONLY)
            result = orchestrator.run(test_case.question)
            
            if result is None:
                print("    ⚠️ Warning: orchestrator returned None")
                # Create dummy result to continue
                result = {
                    "answer": "ERROR: No answer returned",
                    "route": "unknown",
                    "sources": [],
                    "confidence": 0.0,
                    "reason": "System error"
                }
            
            # Handle None answers (unanswerable questions)
            if result['answer'] is None:
                result['answer'] = "No information available"
            
            rag_results.append(result)
            
            print(f"    Route: {result['route']}")
            answer_preview = str(result['answer'])[:60] if result['answer'] else "No answer"
            print(f"    Answer: {answer_preview}...")
            
        except Exception as e:
            print(f"    ❌ Error running question: {e}")
            # Create error result
            rag_results.append({
                "answer": f"ERROR: {str(e)}",
                "route": "error",
                "sources": [],
                "confidence": 0.0,
                "reason": str(e)
            })
    
    print(f"\n✅ Collected {len(rag_results)} RAG outputs")
    
    # Step 4: Initialize Gemini judge
    print("\n[4/7] Initializing Gemini judge...")
    
    try:
        judge = GeminiJudge(model="gemini-2.5-flash")
        evaluator = RAGEvaluator(judge=judge)
        print("✅ Judge initialized")
    except Exception as e:
        print(f"❌ Error initializing judge: {e}")
        print("\nMake sure GOOGLE_API_KEY is set in your .env file")
        print("Get API key from: https://aistudio.google.com/app/apikey")
        return
    
    # Step 5: Run evaluation
    print("\n[5/7] Running evaluation...")
    
    try:
        results = evaluator.evaluate_all(test_cases, rag_results)
    except Exception as e:
        print(f"❌ Error during evaluation: {e}")
        return
    
    # Step 6: Display results
    print("\n[6/7] Displaying results...")
    
    print("\n" + "="*70)
    print("📊 EVALUATION RESULTS")
    print("="*70)
    
    for r in results:
        print(f"\n{r.question_id}: {r.question[:55]}...")
        print(f"  Route: {r.route}")
        print(f"  A. Answer Correctness: {r.answer_correctness.score:.1f}")
        print(f"  B. Context Relevancy:  {r.context_relevancy.score:.1f}")
        print(f"  C. Context Recall:     {r.context_recall.score:.1f}")
        print(f"  Final Score:           {r.final_score:.2f}")
    
    # Compute averages
    avg_correctness = sum(r.answer_correctness.score for r in results) / len(results)
    avg_relevancy = sum(r.context_relevancy.score for r in results) / len(results)
    avg_recall = sum(r.context_recall.score for r in results) / len(results)
    avg_final = sum(r.final_score for r in results) / len(results)
    
    print("\n" + "="*70)
    print("📈 AVERAGE SCORES")
    print("="*70)
    print(f"  A. Answer Correctness: {avg_correctness:.2f}")
    print(f"  B. Context Relevancy:  {avg_relevancy:.2f}")
    print(f"  C. Context Recall:     {avg_recall:.2f}")
    print(f"  Final Score:           {avg_final:.2f}")
    print("="*70)
    
    # Step 7: Save results
    print("\n[7/7] Saving results...")
    
    output_file = eval_dir / "evaluation_results.json"
    evaluator.save_results(results, str(output_file))
    
    print("\n" + "="*70)
    print("✅ EVALUATION COMPLETE!")
    print("="*70)
    print(f"\nResults saved to: {output_file}")
    print(f"Total test cases: {len(results)}")
    print(f"Average score: {avg_final:.2f}")


if __name__ == "__main__":
    main()

