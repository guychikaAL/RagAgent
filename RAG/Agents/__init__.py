"""
Agents Layer

Multi-agent orchestration for RAG query processing.

Architecture:
- Router Agent: Classifies questions (needle vs summary)
- Needle Agent: Extracts atomic facts (high precision)
- Summary Agent: Contextual synthesis (high recall)
- Orchestrator: Multi-agent coordination [TODO]

Usage:
    from RAG.Agents import RouterAgent, NeedleAgent, SummaryAgent
    
    # Step 1: Route the question
    router = RouterAgent()
    route = router.route("Describe the accident")
    # -> {"route": "summary", "confidence": 0.95, "reason": "..."}
    
    # Step 2: Answer with appropriate agent
    if route["route"] == "needle":
        agent = NeedleAgent()
        answer = agent.answer("What is the claim number?", needle_retriever)
        # -> {"answer": "CLM-2024-00789", "confidence": 0.95, ...}
    else:
        agent = SummaryAgent()
        answer = agent.answer("Describe the accident", summary_retriever)
        # -> {"answer": "The accident occurred on...", "confidence": 0.90, ...}
"""

from .router_agent import RouterAgent
from .needle_agent import NeedleAgent
from .summary_agent import SummaryAgent

__all__ = ["RouterAgent", "NeedleAgent", "SummaryAgent"]

