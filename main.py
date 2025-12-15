"""
MAIN ENTRY POINT - RAG System Interactive Q&A
==================================================

This is the main file to run your RAG system.
It loads the pre-built index and lets you ask questions INSTANTLY.

Prerequisites:
    Run build_production_index.py ONCE first!

Usage:
    python main.py

Then type your questions and get instant answers!
"""

import sys
from pathlib import Path
from dotenv import load_dotenv

# Setup
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
load_dotenv(project_root / ".env")

from RAG.Index_Layer.index_layer import ClaimIndexManager
from RAG.Agents import RouterAgent, NeedleAgent, SummaryAgent
from RAG.Orchestration import Orchestrator


def initialize_orchestrator(pdf_path: str = "auto_claim_20_forms_FINAL.pdf", 
                           persist_dir: str = "production_index",
                           force_rebuild: bool = False):
    """
    Initialize orchestrator with optional index building.
    
    Args:
        pdf_path: Path to the PDF file (used if force_rebuild=True)
        persist_dir: Directory to load/save the index
        force_rebuild: If True, rebuild the index from PDF. If False, load existing index.
    
    Returns:
        Orchestrator instance or None if index doesn't exist and force_rebuild=False
    """
    
    print("="*70)
    print("⚡ INITIALIZING ORCHESTRATOR")
    print("="*70)
    
    index_path = Path(persist_dir)
    
    # Handle force rebuild
    if force_rebuild:
        print(f"\n🔄 Force rebuild requested - building index from {pdf_path}...")
        
        # Build index from scratch (handles full pipeline internally)
        index_manager = ClaimIndexManager()
        index_manager.build_index(
            pdf_path=pdf_path, 
            persist_dir=persist_dir,
            index_all_claims=True  # Index all 19 claims
        )
        print("✅ Index built and saved")
    else:
        # Load existing index
        if not index_path.exists():
            print(f"\n❌ Error: Index not found at '{persist_dir}'!")
            print("\n💡 Options:")
            print(f"   1. Set force_rebuild=True to build from {pdf_path}")
            print("   2. Run: python build_production_index.py")
            return None
        
        print(f"\n[1/3] 📂 Loading index from {persist_dir}...")
        index_manager = ClaimIndexManager()
        index_manager.load_index(persist_dir=persist_dir)
        print("✅ Index loaded")
    
    # Create retrievers and query engines
    print("\n[2/3] 🔍 Creating retrievers and query engines...")
    needle_retriever = index_manager.get_needle_retriever(
        top_k=5,
        similarity_threshold=0.7,
    )
    
    map_reduce_query_engine = index_manager.get_map_reduce_query_engine(
        top_k=30,
    )
    print("✅ Retrievers and query engines ready")
    
    # Initialize agents
    print("\n[3/3] 🤖 Initializing agents...")
    router_agent = RouterAgent(model="gpt-4o-mini", temperature=0.0)
    needle_agent = NeedleAgent(
        model="gpt-4o-mini", 
        temperature=0.0,
        enable_mcp_tools=True
    )
    summary_agent = SummaryAgent(
        model="gpt-4o-mini", 
        temperature=0.2,
        enable_mcp_tools=True
    )
    
    orchestrator = Orchestrator(
        router_agent=router_agent,
        needle_agent=needle_agent,
        summary_agent=summary_agent,
        needle_retriever=needle_retriever,
        map_reduce_query_engine=map_reduce_query_engine,
    )
    print("✅ Agents ready")
    
    print("\n" + "="*70)
    print("✅ ORCHESTRATOR READY!")
    print("="*70)
    
    return orchestrator


def load_system():
    """Load the pre-built index and initialize agents."""
    
    print("="*70)
    print("⚡ LOADING PRODUCTION SYSTEM")
    print("="*70)
    
    # Check if index exists
    index_path = Path("production_index")
    if not index_path.exists():
        print("\n❌ Error: Production index not found!")
        print("\n💡 Run this first:")
        print("   python build_production_index.py")
        return None
    
    # Load index (FAST!)
    print("\n[1/3] 📂 Loading pre-built index...")
    index_manager = ClaimIndexManager()
    index_manager.load_index(persist_dir="production_index")
    print("✅ Index loaded (INSTANT!)")
    
    # Create retrievers and query engines
    print("\n[2/3] 🔍 Creating retrievers and query engines...")
    needle_retriever = index_manager.get_needle_retriever(
        top_k=5,
        similarity_threshold=0.7,
    )
    
    # Get MapReduce query engine for comprehensive summarization
    map_reduce_query_engine = index_manager.get_map_reduce_query_engine(
        top_k=30,  # Increased to ensure all 20 claims are covered (was 15)
    )
    print("✅ Retrievers and query engines ready")
    
    # Initialize agents (WITH MCP TOOLS!)
    print("\n[3/3] 🤖 Initializing agents...")
    router_agent = RouterAgent(model="gpt-4o-mini", temperature=0.0)
    needle_agent = NeedleAgent(
        model="gpt-4o-mini", 
        temperature=0.0,
        enable_mcp_tools=True  # ✅ MCP tools enabled!
    )
    summary_agent = SummaryAgent(
        model="gpt-4o-mini", 
        temperature=0.2,
        enable_mcp_tools=True  # ✅ MCP tools enabled!
    )
    
    # Create orchestrator with MapReduce
    orchestrator = Orchestrator(
        router_agent=router_agent,
        needle_agent=needle_agent,
        summary_agent=summary_agent,
        needle_retriever=needle_retriever,
        map_reduce_query_engine=map_reduce_query_engine,  # MapReduce for summaries
    )
    print("✅ Agents ready")
    
    print("\n" + "="*70)
    print("✅ SYSTEM READY!")
    print("="*70)
    
    return orchestrator


def interactive_mode(orchestrator):
    """Interactive question-answering loop."""
    
    print("\n" + "="*70)
    print("💬 INTERACTIVE MODE - Ask Questions About ANY Claim!")
    print("="*70)
    
    print("\n📋 You can ask about ANY of the 19 claimants:")
    print("   • Sarah Klein, David Ross, Mia Thompson, Eli Cohen,")
    print("   • Lucas Rivera, Nora Bennett, Adam Levi, Daniela Ruiz,")
    print("   • Aaron Blake, Maya Gold, Oren Shapiro, Sophia Lane,")
    print("   • Ethan Hall, Julia Marks, Ben Adler, Rachel Stern,")
    print("   • Noah Hart, Emily Vance, Lior Avraham")
    
    print("\n💡 Example Questions:")
    print("   - What is Lior Avraham's phone number?")
    print("   - What is Sarah Klein's account number?")
    print("   - Summarize claim number 5")
    print("   - What happened in David Ross's accident?")
    print("   - What vehicle does Mia Thompson drive?")
    print("   - How many days between Jon Mor's accident and repair? 🔧 (MCP TOOL!)")
    
    print("\nType 'quit' or 'exit' to stop.")
    print("="*70)
    
    question_count = 0
    
    while True:
        # Get question
        try:
            question = input("\n❓ Your question: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\n👋 Goodbye!")
            break
        
        # Check for exit
        if question.lower() in ['quit', 'exit', 'q', 'bye']:
            print("\n👋 Goodbye!")
            break
        
        # Skip empty
        if not question:
            print("⚠️  Please enter a question.")
            continue
        
        # Process question (FAST!)
        question_count += 1
        print(f"\n⚡ Processing question #{question_count}...")
        
        try:
            # Run orchestrator (no rebuilding!)
            result = orchestrator.run(question)
            
            # Display result
            print("\n" + "="*70)
            print("📊 ANSWER")
            print("="*70)
            print(f"\n🔀 Route:      {result['route'].upper()}")
            print(f"💡 Answer:     {result['answer']}")
            print(f"🎯 Confidence: {result['confidence']:.0%}")
            print(f"📚 Sources:    {len(result['sources'])} chunk(s)")
            print("="*70)
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            continue


def main():
    """Main entry point."""
    
    # Load system
    orchestrator = load_system()
    
    if orchestrator is None:
        return
    
    # Start interactive mode
    interactive_mode(orchestrator)


if __name__ == "__main__":
    main()

