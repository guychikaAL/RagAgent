"""
====================================================
RAGAS EVALUATION - Main Evaluation Logic
====================================================

This module runs RAGAS evaluation on the existing RAG system.

CRITICAL PRINCIPLES:
- Does NOT modify RAG system
- Runs OFFLINE ONLY
- Uses Gemini as LLM (NOT OpenAI)
- Reads test cases from existing evaluation/
- Calls existing RAG system via query pipeline

FLOW:
1. Load test cases
2. Query RAG system for each test case
3. Collect: question, answer, contexts, ground_truth
4. Build RAGAS dataset
5. Initialize Gemini LLM via LangChain
6. Run RAGAS evaluation
7. Save results to JSON

====================================================
"""

import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import pandas as pd

try:
    from datasets import Dataset
except ImportError:
    raise ImportError("Please install: pip install datasets")

try:
    from ragas import evaluate
except ImportError:
    raise ImportError("Please install: pip install ragas")

try:
    from langchain_openai import ChatOpenAI
except ImportError:
    raise ImportError("Please install: pip install langchain-openai")

# Add parent directory to path to import from RAG
sys.path.insert(0, str(Path(__file__).parent.parent))

from RAG.Index_Layer.index_layer import ClaimIndexManager
from RAG.Agents.router_agent import RouterAgent
from RAG.Agents.needle_agent import NeedleAgent
from RAG.Agents.summary_agent import SummaryAgent
from RAG.Orchestration.orchestrator import Orchestrator

# Import from local ragas_metrics in same directory
# WHY: Directory name has hyphen, so we import directly from same directory
try:
    # Try direct import first (when run as script)
    from ragas_metrics import RAGAS_METRICS, METRIC_NAMES
except ImportError:
    # Fallback to relative import (when imported as module)
    from .ragas_metrics import RAGAS_METRICS, METRIC_NAMES


class RAGASEvaluator:
    """
    RAGAS-based evaluator for RAG system.
    
    WHY THIS CLASS:
    - Encapsulates RAGAS evaluation logic
    - Integrates with existing RAG system
    - Uses Gemini as evaluation LLM
    - Stores results for analysis
    
    CRITICAL: This is a READ-ONLY evaluation layer.
    """
    
    def __init__(self, index_dir: str = "production_index"):
        """
        Initialize RAGAS evaluator.
        
        Args:
            index_dir: Path to production index
        """
        # Initialize RAG system (read-only)
        print("🔧 Initializing RAG system...")
        
        # Load index
        print("   [1/3] Loading index...")
        index_manager = ClaimIndexManager()
        index_manager.load_index(persist_dir=index_dir)
        
        # Create retrievers and query engines
        print("   [2/3] Creating retrievers...")
        needle_retriever = index_manager.get_needle_retriever(
            top_k=3,              # Reduced from 5 - fewer chunks for atomic facts
            similarity_threshold=0.75,  # Increased from 0.7 - filter marginal matches
        )
        map_reduce_query_engine = index_manager.get_map_reduce_query_engine(
            top_k=15,
        )
        
        # Initialize agents
        print("   [3/3] Initializing agents...")
        router_agent = RouterAgent(model="gpt-4o-mini", temperature=0.0)
        needle_agent = NeedleAgent(model="gpt-4o-mini", temperature=0.0)
        summary_agent = SummaryAgent(model="gpt-4o-mini", temperature=0.2)
        
        # Create orchestrator
        self.orchestrator = Orchestrator(
            router_agent=router_agent,
            needle_agent=needle_agent,
            summary_agent=summary_agent,
            needle_retriever=needle_retriever,
            map_reduce_query_engine=map_reduce_query_engine,
        )
        
        # Initialize OpenAI LLM for RAGAS
        print("\n🔧 Initializing OpenAI LLM for RAGAS...")
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY not found. "
                "Set it in environment or .env file."
            )
        
        # Create OpenAI LLM via LangChain wrapper
        # WHY gpt-4o-mini: Fast, cost-effective, reliable for evaluation
        # More stable than Gemini experimental models
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            api_key=api_key,
            temperature=0.0,  # Deterministic for evaluation
            timeout=60,  # Timeout for API calls
            max_retries=3,  # Retry failed requests
        )
        
        print("✅ RAGAS Evaluator initialized")
    
    def load_test_cases(
        self, 
        test_cases_path: str,
        max_cases: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Load test cases from JSON.
        
        Args:
            test_cases_path: Path to test_cases.json
            max_cases: Optional limit on number of test cases to load
                      (useful for avoiding API rate limits)
            
        Returns:
            List of test case dictionaries
        """
        with open(test_cases_path, 'r') as f:
            data = json.load(f)
        
        test_cases = data["test_cases"]
        
        # Limit number of cases if specified
        if max_cases is not None and max_cases > 0:
            test_cases = test_cases[:max_cases]
            print(f"⚠️  Limited to first {len(test_cases)} test cases (to avoid API rate limits)")
        
        return test_cases
    
    def query_rag_system(self, question: str) -> Dict[str, Any]:
        """
        Query the RAG system and collect outputs.
        
        Args:
            question: User question
            
        Returns:
            Dictionary with:
                - answer: System's answer
                - contexts: List of retrieved chunk texts
                - sources: List of chunk IDs
                - route: Routing decision
                - confidence: Confidence score
        """
        # Query orchestrator
        result = self.orchestrator.run(question)
        
        # Extract answer
        answer = result["answer"]
        
        # Extract contexts (chunk texts)
        # WHY: RAGAS needs actual text, not IDs
        contexts = result.get("retrieved_chunks_content", [])
        
        # Extract metadata
        sources = result.get("sources", [])
        route = result.get("route", "unknown")
        confidence = result.get("confidence", 0.0)
        
        return {
            "answer": answer,
            "contexts": contexts,
            "sources": sources,
            "route": route,
            "confidence": confidence,
        }
    
    def build_ragas_dataset(
        self,
        test_cases: List[Dict[str, Any]],
    ) -> Dataset:
        """
        Build RAGAS dataset from test cases.
        
        WHY THIS METHOD:
        - RAGAS requires specific dataset format
        - Must include: question, answer, contexts, ground_truth
        - Uses Hugging Face Dataset format
        
        Args:
            test_cases: List of test cases
            
        Returns:
            Hugging Face Dataset for RAGAS
        """
        print(f"\n📊 Building RAGAS dataset from {len(test_cases)} test cases...")
        
        dataset_dict = {
            "question": [],
            "answer": [],
            "contexts": [],
            "ground_truth": [],
        }
        
        for i, test_case in enumerate(test_cases, 1):
            question = test_case["question"]
            ground_truth = test_case["ground_truth"]
            
            print(f"   [{i}/{len(test_cases)}] Querying: {test_case['id']}")
            
            # Query RAG system
            rag_result = self.query_rag_system(question)
            
            # Add to dataset
            dataset_dict["question"].append(question)
            dataset_dict["answer"].append(rag_result["answer"])
            dataset_dict["contexts"].append(rag_result["contexts"])
            dataset_dict["ground_truth"].append(ground_truth)
        
        # Convert to Hugging Face Dataset
        dataset = Dataset.from_dict(dataset_dict)
        
        print(f"✅ Dataset built: {len(dataset)} samples")
        
        return dataset
    
    def run_evaluation(
        self,
        dataset: Dataset,
    ) -> Any:
        """
        Run RAGAS evaluation.
        
        Args:
            dataset: RAGAS dataset
            
        Returns:
            RAGAS evaluation results (Result object)
        """
        print(f"\n🔬 Running RAGAS evaluation...")
        print(f"   Metrics: {', '.join(METRIC_NAMES)}")
        print(f"   LLM: OpenAI GPT-4o-mini")
        print(f"   Samples: {len(dataset)}")
        print(f"\n⚠️  Note: This may take a few minutes due to multiple metric evaluations...")
        print(f"   RAGAS will retry automatically on any failures.")
        
        try:
            # Run RAGAS evaluate
            # WHY: Uses Gemini for all LLM-based metrics
            results = evaluate(
                dataset=dataset,
                metrics=RAGAS_METRICS,
                llm=self.llm,
            )
            
            print(f"\n✅ RAGAS evaluation complete")
            
        except Exception as e:
            print(f"\n⚠️  RAGAS evaluation completed with errors: {e}")
            print(f"   Some metrics may be missing or incomplete.")
            # Return empty result that will be handled by save_results
            results = None
        
        return results
    
    def save_results(
        self,
        results: Any,
        dataset: Dataset,
        output_path: str,
    ) -> None:
        """
        Save RAGAS results to JSON.
        
        Args:
            results: RAGAS evaluation results (Result object)
            dataset: Original dataset (for questions)
            output_path: Path to save results
        """
        # Convert RAGAS Result object to dictionary
        # RAGAS returns a Result object with a to_pandas() method
        if results is None:
            print(f"⚠️  No RAGAS results to save (evaluation may have failed)")
            results_df = pd.DataFrame()
        else:
            try:
                # Try to convert to pandas DataFrame first
                results_df = results.to_pandas()
                print(f"✅ Converted RAGAS results to DataFrame: {len(results_df)} rows")
            except Exception as e:
                print(f"⚠️  Could not convert RAGAS results to DataFrame: {e}")
                # Try to access as dictionary
                try:
                    results_df = pd.DataFrame([results])
                except Exception as e2:
                    print(f"❌ Failed to process RAGAS results: {e2}")
                    # Fallback: create empty results
                    results_df = pd.DataFrame()
        
        # Extract per-question scores
        results_list = []
        
        for i in range(len(dataset)):
            result_dict = {
                "question_id": f"q{i+1}",
                "question": dataset[i]["question"],
                "answer": dataset[i]["answer"],
                "ground_truth": dataset[i]["ground_truth"],
            }
            
            # Add metric scores from DataFrame if available
            if len(results_df) > 0 and i < len(results_df):
                for metric_name in METRIC_NAMES:
                    if metric_name in results_df.columns:
                        value = results_df.iloc[i][metric_name]
                        # Handle NaN values
                        if pd.isna(value):
                            result_dict[metric_name] = None
                        else:
                            result_dict[metric_name] = float(value)
                    else:
                        result_dict[metric_name] = None
            else:
                # No scores available
                for metric_name in METRIC_NAMES:
                    result_dict[metric_name] = None
            
            results_list.append(result_dict)
        
        # Compute average scores
        summary: Dict[str, Any] = {
            "total_cases": len(dataset),
        }
        
        if len(results_df) > 0:
            for metric_name in METRIC_NAMES:
                if metric_name in results_df.columns:
                    # Compute mean, ignoring NaN values
                    mean_score = results_df[metric_name].mean()
                    # Check if mean_score is NaN or None
                    try:
                        score_float = float(mean_score)
                        if not (score_float != score_float):  # NaN check (NaN != NaN is True)
                            summary[f"avg_{metric_name}"] = score_float
                        else:
                            summary[f"avg_{metric_name}"] = 0.0
                    except (ValueError, TypeError):
                        summary[f"avg_{metric_name}"] = 0.0
                else:
                    summary[f"avg_{metric_name}"] = 0.0
        else:
            # No results available
            for metric_name in METRIC_NAMES:
                summary[f"avg_{metric_name}"] = 0.0
        
        # Build output
        output_data = {
            "results": results_list,
            "summary": summary,
        }
        
        # Save to file
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"\n✅ Results saved to: {output_file}")
        
        # Print summary
        print(f"\n" + "="*70)
        print(f"📊 RAGAS EVALUATION SUMMARY")
        print(f"="*70)
        print(f"Total test cases: {summary['total_cases']}")
        print(f"\nAverage Scores:")
        for metric_name in METRIC_NAMES:
            key = f"avg_{metric_name}"
            if key in summary:
                print(f"  {metric_name}: {summary[key]:.3f}")
        print(f"="*70)


def main():
    """
    Main evaluation script.
    
    WHY THIS FUNCTION:
    - Entry point for running RAGAS evaluation
    - Uses existing test cases
    - Saves results for analysis
    """
    # Determine project root (parent of evaluation-ragas directory)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    # Load .env file from project root
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ Loaded .env from: {env_path}\n")
    else:
        print(f"⚠️  No .env file found at: {env_path}")
        print("   Checking environment variables instead...\n")
    
    # Check required API keys
    print("="*70)
    print("🔑 Checking API Keys...")
    print("="*70)
    
    openai_key = os.getenv("OPENAI_API_KEY")
    
    if not openai_key:
        print("\n❌ Missing required API key: OPENAI_API_KEY")
        print("\n💡 Set it in your environment or .env file:")
        print("   export OPENAI_API_KEY='your-openai-key'")
        print("\nOr add to .env file in project root:")
        print("   OPENAI_API_KEY=your-openai-key")
        return
    else:
        print("✅ OPENAI_API_KEY found")
    
    print("\n" + "="*70)
    
    # Paths relative to project root
    test_cases_path = project_root / "evaluation" / "test_cases.json"
    output_path = script_dir / "ragas_results.json"
    index_dir = project_root / "production_index"
    
    # Convert to strings
    test_cases_path = str(test_cases_path)
    output_path = str(output_path)
    index_dir = str(index_dir)
    
    # Initialize evaluator
    evaluator = RAGASEvaluator(index_dir=index_dir)
    
    # Load test cases (using all 8 tests)
    # WHY: OpenAI API is more stable than Gemini, can handle full test suite
    test_cases = evaluator.load_test_cases(test_cases_path, max_cases=None)
    print(f"📂 Loaded {len(test_cases)} test cases")
    
    # Build RAGAS dataset
    dataset = evaluator.build_ragas_dataset(test_cases)
    
    # Run evaluation
    results = evaluator.run_evaluation(dataset)
    
    # Save results
    evaluator.save_results(results, dataset, output_path)


if __name__ == "__main__":
    main()
