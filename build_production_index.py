"""
BUILD PRODUCTION INDEX - Run Once
==================================

This script builds the index ONCE and saves it to disk.
Run this script first, then use main.py for fast queries.

Usage:
    python build_production_index.py

This will:
1. Load PDF
2. Process ALL 19 claims
3. Build vector indexes
4. Save to disk (~2-3 minutes)

Then you can query instantly with main.py!
"""

import sys
from pathlib import Path
from dotenv import load_dotenv

# Setup
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
load_dotenv(project_root / ".env")

from RAG.app import create_rag_application


def main():
    print("="*70)
    print("🏭 BUILDING PRODUCTION INDEX")
    print("="*70)
    print("\nThis will take ~2-3 minutes.")
    print("Run this ONCE, then use main.py for instant queries!\n")
    
    # PDF path
    pdf_path = str(project_root / "auto_claim_20_forms_FINAL.pdf")
    
    if not Path(pdf_path).exists():
        print(f"❌ Error: PDF not found at {pdf_path}")
        return
    
    # Create app
    app = create_rag_application(
        embedding_model="text-embedding-3-small",
        llm_model="gpt-4o-mini",
    )
    
    # Build index with ALL claims
    print("\n🚀 Building index for ALL 19 claims...")
    print("   (This processes the entire PDF and creates embeddings)\n")
    
    # We'll use the app but save the index
    # For now, let's use ClaimIndexManager directly for better control
    from RAG.Index_Layer.index_layer import ClaimIndexManager
    
    index_manager = ClaimIndexManager()
    index_manager.build_index(
        pdf_path=pdf_path,
        persist_dir="production_index",
        index_all_claims=True,
    )
    
    print("\n" + "="*70)
    print("✅ PRODUCTION INDEX BUILT!")
    print("="*70)
    print("\n📁 Index saved to: production_index/")
    print("\n🚀 Next steps:")
    print("   1. Run: python main.py")
    print("   2. Ask unlimited questions INSTANTLY!")
    print("   3. No rebuilding needed!")
    print("\n" + "="*70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

