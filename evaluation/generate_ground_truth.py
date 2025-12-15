"""
Generate Ground Truth for Test Cases

This script runs questions through the RAG system and shows the actual answers,
so you can update test_cases.json with correct ground truth.

Usage:
    python generate_ground_truth.py
"""

import sys
from pathlib import Path
from dotenv import load_dotenv

# Setup
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
load_dotenv(project_root / ".env")

from RAG.Index_Layer.index_layer import ClaimIndexManager
from RAG.Agents import RouterAgent, NeedleAgent, SummaryAgent
from RAG.Orchestration import Orchestrator

print("🚀 Loading RAG system...")

# Load system
index_manager = ClaimIndexManager()
index_manager.load_index(persist_dir="../production_index")

needle_retriever = index_manager.get_needle_retriever(top_k=5, similarity_threshold=0.7)
map_reduce_query_engine = index_manager.get_map_reduce_query_engine(top_k=15)

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

print("✅ RAG system ready\n")
print("="*70)
print("📋 GENERATING GROUND TRUTH")
print("="*70)

# Questions from test_cases.json
questions = [
    ("needle_001", "What is Jon Mor's phone number?"),
    ("needle_002", "What is Eli Cohen's account number?"),
    ("needle_003", "What vehicle does Sarah Klein drive?"),
    ("needle_004", "When did David Ross's accident occur?"),
    ("summary_001", "Summarize Jon Mor's entire claim"),
    ("summary_002", "Summarize Eli Cohen's claim"),
    ("summary_003", "What happened in Sarah Klein's accident?"),
    ("unanswerable_001", "What is the blood type of the claimant in claim #1?"),
]

for test_id, question in questions:
    print(f"\n{test_id}:")
    print(f"  Question: {question}")
    
    result = orchestrator.run(question)
    
    answer = result['answer'] if result['answer'] is not None else "No information available"
    
    print(f"  Answer: {answer}")
    print(f"  Route: {result['route']}")
    print(f"  Chunks: {len(result['sources'])}")
    print()
    print(f'  Update test_cases.json with:')
    print(f'  "ground_truth": "{answer}"')
    print("  " + "-"*66)

print("\n" + "="*70)
print("✅ DONE! Update test_cases.json with the answers above")
print("="*70)

