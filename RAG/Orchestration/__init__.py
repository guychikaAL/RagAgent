"""
Orchestration Layer

Coordinates multi-agent RAG pipeline.

Architecture:
- Orchestrator: Routes questions to appropriate agent
- Uses Router Agent for classification
- Delegates to Needle or Summary Agent
- Returns unified response format

Usage:
    from RAG.Orchestration import Orchestrator
    from RAG.Agents import RouterAgent, NeedleAgent, SummaryAgent
    
    # Initialize agents and retrievers
    router = RouterAgent()
    needle_agent = NeedleAgent()
    summary_agent = SummaryAgent()
    
    # Create orchestrator
    orchestrator = Orchestrator(
        router_agent=router,
        needle_agent=needle_agent,
        summary_agent=summary_agent,
        needle_retriever=needle_retriever,
        summary_retriever=summary_retriever
    )
    
    # Run pipeline
    result = orchestrator.run("What is the claim number?")
    # -> {"route": "needle", "answer": "CLM-2024-00789", ...}
"""

from .orchestrator import Orchestrator

__all__ = ["Orchestrator"]

