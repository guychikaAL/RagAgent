"""
Simple GUI App for Auto Claims RAG System
==========================================

A simple web-based interface to ask questions about auto_claim_20_forms_FINAL.pdf

Run with: streamlit run gui_app.py
"""

import streamlit as st
import sys
import subprocess
import json
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Load environment variables from .env file
project_root = Path(__file__).parent.parent
env_path = project_root / ".env"
load_dotenv(env_path)

# Add parent directory to path for imports
sys.path.insert(0, str(project_root))

from RAG.Index_Layer.index_layer import ClaimIndexManager
from RAG.Agents.router_agent import RouterAgent
from RAG.Agents.needle_agent import NeedleAgent
from RAG.Agents.summary_agent import SummaryAgent
from RAG.Orchestration.orchestrator import Orchestrator

# Page configuration
st.set_page_config(
    page_title="Auto Claims Q&A",
    page_icon="🚗",
    layout="centered"
)

# Initialize session state for RAG system
@st.cache_resource
def initialize_rag_system():
    """Initialize the RAG system (cached to avoid reloading)."""
    
    with st.spinner("🔧 Loading RAG system..."):
        # Load index
        index_manager = ClaimIndexManager()
        index_manager.load_index(persist_dir="production_index")
        
        # Create retrievers
        needle_retriever = index_manager.get_needle_retriever(
            top_k=3,
            similarity_threshold=0.75,
        )
        map_reduce_query_engine = index_manager.get_map_reduce_query_engine(
            top_k=30,  # Increased to ensure all 20 claims are covered
        )
        
        # Initialize agents (WITH MCP TOOLS!)
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
        
        # Create orchestrator
        orchestrator = Orchestrator(
            router_agent=router_agent,
            needle_agent=needle_agent,
            summary_agent=summary_agent,
            needle_retriever=needle_retriever,
            map_reduce_query_engine=map_reduce_query_engine,
        )
        
    return orchestrator

# Header
st.title("🚗 Auto Claims Q&A System")
st.markdown("### Hello! Ask me anything about auto_claim_20_forms_FINAL.pdf")
st.markdown("---")

# Info box
with st.expander("ℹ️ How to use this app"):
    st.markdown("""
    **What you can ask:**
    - Specific facts: *"What is Jon Mor's phone number?"*
    - Summaries: *"Summarize Jon Mor's entire claim"*
    - Details: *"When did David Ross's accident occur?"*
    - Date calculations: *"How many days between Jon Mor's accident and repair?"*
    
    **The system will:**
    - Route your question to the right agent (NEEDLE or SUMMARY)
    - Retrieve relevant information from the claims
    - Use MCP tools for precise date calculations (🔧 shown when used)
    - Provide accurate, grounded answers
    - Show sources and confidence scores
    """)

# Check for API key first
import os
if not os.getenv("OPENAI_API_KEY"):
    st.error("❌ OPENAI_API_KEY not found!")
    st.markdown("""
    **Please set your OpenAI API key:**
    
    1. Create a `.env` file in the project root
    2. Add this line:
       ```
       OPENAI_API_KEY=your-api-key-here
       ```
    3. Restart the app
    
    Or set it in your environment:
    ```bash
    export OPENAI_API_KEY='your-api-key-here'
    ```
    """)
    st.stop()

# Initialize RAG system
try:
    orchestrator = initialize_rag_system()
    st.success("✅ RAG system ready!")
except Exception as e:
    st.error(f"❌ Failed to initialize RAG system: {e}")
    with st.expander("🔍 Error Details"):
        st.exception(e)
    st.stop()

# Initialize session state
if 'question_text' not in st.session_state:
    st.session_state.question_text = ""
if 'trigger_search' not in st.session_state:
    st.session_state.trigger_search = False

# Question input - use session state key to bind automatically
st.markdown("### 💬 Ask Your Question")
question = st.text_input(
    "Enter your question:",
    value=st.session_state.question_text,
    placeholder="e.g., What is Jon Mor's phone number?",
    label_visibility="collapsed",
)

# Submit button
submit_clicked = st.button("🔍 Get Answer", type="primary", use_container_width=True)

# Determine if we should process the query
should_process = submit_clicked or st.session_state.trigger_search

# Show indicator if triggered by example
if st.session_state.trigger_search and not submit_clicked:
    st.info("🎯 Running example question...")

# Reset trigger after checking
if st.session_state.trigger_search:
    st.session_state.trigger_search = False

if should_process:
    if not question or not question.strip():
        st.warning("⚠️ Please enter a question first!")
    else:
        with st.spinner("🤔 Thinking..."):
            try:
                # Query the RAG system
                result = orchestrator.run(question)
                
                # Check if MCP tool was used
                mcp_used = result.get("mcp_tool_used", False)
                mcp_tool_name = result.get("mcp_tool_name")
                mcp_tool_details = result.get("mcp_tool_details", {})
                
                # Display answer
                st.markdown("### 💡 Answer")
                answer = result.get("answer")
                
                if answer is None or answer == "":
                    st.info("🤷 No information found for this question.")
                else:
                    st.success(answer)
                
                # Highlight MCP tool usage if detected - PROMINENTLY!
                if mcp_used:
                    st.success(f"🔧 **MCP Tool Used: `{mcp_tool_name}`**")
                    st.info(f"""
                    **Tool Details:**
                    - Start Date: `{mcp_tool_details.get('start_date', 'N/A')}`
                    - End Date: `{mcp_tool_details.get('end_date', 'N/A')}`
                    - Result: `{mcp_tool_details.get('result', 'N/A')}`
                    
                    💡 *The agent delegated date calculation to an external tool for precision!*
                    """)
                
                # Show metadata in expandable sections
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric("Route", result.get("route", "N/A").upper())
                    st.metric("Confidence", f"{result.get('confidence', 0):.2f}")
                
                with col2:
                    sources = result.get("sources", [])
                    st.metric("Sources", len(sources))
                    if mcp_used:
                        st.metric("🔧 MCP Tool", "✅ ACTIVE")
                    else:
                        st.metric("🔧 MCP Tool", "⊝ Not Used")
                    
                # Show detailed metadata
                with st.expander("📊 Detailed Metadata"):
                    metadata = {
                        "route": result.get("route"),
                        "confidence": result.get("confidence"),
                        "reason": result.get("reason"),
                        "sources": result.get("sources", [])[:5],  # First 5 sources
                    }
                    
                    # Add MCP tool info if used
                    if mcp_used:
                        metadata["mcp_tool_used"] = True
                        metadata["mcp_tool_name"] = mcp_tool_name
                        metadata["mcp_tool_details"] = mcp_tool_details
                    else:
                        metadata["mcp_tool_used"] = False
                    
                    st.json(metadata)
                
                # Show map-reduce process if available (summary agent)
                map_reduce_steps = result.get("map_reduce_steps")
                if map_reduce_steps and result.get("route") == "summary":
                    with st.expander(f"🗺️ Map-Reduce Process ({map_reduce_steps['total_chunks']} chunks)"):
                        st.markdown("**How Map-Reduce Works:**")
                        st.info("📥 Retrieve chunks → 📝 MAP (summarize each) → 🔄 REDUCE (hierarchical merge) → ✅ Final answer")
                        
                        # Show the process flow
                        st.markdown("### 🔄 Processing Pipeline")
                        for i, step in enumerate(map_reduce_steps['process'], 1):
                            if 'MAP:' in step:
                                st.success(f"**{i}.** {step}")
                            elif 'REDUCE' in step:
                                st.info(f"**{i}.** {step}")
                            elif 'FINAL' in step:
                                st.warning(f"**{i}.** {step}")
                            else:
                                st.write(f"**{i}.** {step}")
                        
                        st.markdown("---")
                        
                        # Show MAP inputs (sample)
                        st.markdown("### 📝 MAP Step (Sample Inputs)")
                        st.caption(f"Showing {len(map_reduce_steps['map_inputs'])} of {map_reduce_steps['total_chunks']} chunks that were individually summarized:")
                        
                        for chunk_info in map_reduce_steps['map_inputs'][:5]:  # Show first 5
                            with st.container():
                                col1, col2 = st.columns([1, 4])
                                with col1:
                                    st.metric(f"Chunk {chunk_info['chunk_number']}", "✓ Mapped")
                                with col2:
                                    with st.expander(f"View Chunk {chunk_info['chunk_number']} content"):
                                        st.text(chunk_info['chunk_preview'])
                                st.divider()
                        
                        if map_reduce_steps['total_chunks'] > 5:
                            st.info(f"... and {map_reduce_steps['total_chunks'] - 5} more chunks (each individually summarized in MAP step)")
                        
                        st.markdown("---")
                        st.markdown("### 🔄 REDUCE Step")
                        st.write(map_reduce_steps['reduce_description'])
                        
                        st.markdown("---")
                        st.markdown("💡 **Each chunk was summarized individually, then hierarchically combined into the final answer!**")
                
                # Show chunk hierarchy if available (auto-merging visualization)
                chunk_hierarchy = result.get("chunk_hierarchy", [])
                if chunk_hierarchy and result.get("route") == "needle":
                    with st.expander(f"🌳 Auto-Merging Hierarchy ({len(chunk_hierarchy)} chunks)"):
                        st.markdown("**How Auto-Merging Works:**")
                        st.info("🔍 System searches **child chunks** (atomic facts) → 🔄 Automatically merges to **parent chunks** (full context)")
                        
                        # Group by parent/child
                        parents = [c for c in chunk_hierarchy if c['chunk_level'] == 'parent']
                        children = [c for c in chunk_hierarchy if c['chunk_level'] == 'child']
                        
                        if parents:
                            st.markdown("### 📦 Parent Chunks (Full Context)")
                            for i, chunk in enumerate(parents, 1):
                                st.markdown(f"**Parent {i}:** `{chunk['chunk_id'][:12]}...`")
                                st.success(f"Score: {chunk['score']:.3f}")
                                with st.expander(f"View Parent {i} content"):
                                    st.text(chunk['text_preview'])
                        
                        if children:
                            st.markdown("### 🔎 Child Chunks (Atomic Facts)")
                            for i, chunk in enumerate(children, 1):
                                parent_id = chunk.get('parent_id', 'none')
                                st.markdown(f"**Child {i}:** `{chunk['chunk_id'][:12]}...` → Parent: `{parent_id[:12] if parent_id else 'none'}...`")
                                st.info(f"Score: {chunk['score']:.3f}")
                                with st.expander(f"View Child {i} content"):
                                    st.text(chunk['text_preview'])
                        
                        st.markdown("---")
                        st.markdown("💡 **The system searched child chunks but returned parent chunks with complete information!**")
                
                # Show retrieved chunks (fallback/simple view)
                chunks = result.get("retrieved_chunks_content", [])
                if chunks and not chunk_hierarchy:
                    with st.expander(f"📄 Retrieved Chunks ({len(chunks)})"):
                        for i, chunk in enumerate(chunks[:3], 1):  # Show first 3
                            st.markdown(f"**Chunk {i}:**")
                            st.text(chunk[:300] + "..." if len(chunk) > 300 else chunk)
                            st.markdown("---")
                
            except Exception as e:
                st.error(f"❌ Error processing question: {e}")
                st.exception(e)

# Sidebar with system info
with st.sidebar:
    st.markdown("## ⚙️ System Info")
    st.markdown("""
    **Document:**  
    📄 auto_claim_20_forms_FINAL.pdf
    
    **Components:**
    - 🧠 Router Agent (gpt-4o-mini)
    - 🎯 Needle Agent (specific facts)
    - 📊 Summary Agent (broad questions)
    - 🔧 MCP Tools (date calculations)
    - 🔍 Vector Index (embeddings)
    """)
    
    st.markdown("---")
    st.markdown("### 📚 Example Questions")
    
    # Organize by category
    st.markdown("**🎯 Needle Questions (Specific Facts):**")
    needle_questions = [
        "What is Jon Mor's phone number?",
        "What is the phone number in claim number 5?",
        "What was the officer badge ID in Nora Bennett's claim?",
    ]
    
    for i, eq in enumerate(needle_questions):
        if st.button(eq, key=f"needle_{i}", use_container_width=True):
            st.session_state.question_text = eq
            st.session_state.trigger_search = True
            st.rerun()
    
    st.markdown("**🔧 MCP Tool Questions (Date Calculations):**")
    mcp_questions = [
        "How many days between Sarah Klein's accident and repair?",
    ]
    
    for i, eq in enumerate(mcp_questions):
        if st.button(f"🔧 {eq}", key=f"mcp_{i}", use_container_width=True):
            st.session_state.question_text = eq
            st.session_state.trigger_search = True
            st.rerun()
    
    st.markdown("**📊 Summary Questions (Broad Context):**")
    summary_questions = [
        "Summarize claim number 10",
        "What happened in David Ross's accident?",
        "Can you tell me the weather condition in most accidents where the repair estimate is the highest?",
    ]
    
    for i, eq in enumerate(summary_questions):
        if st.button(eq, key=f"summary_{i}", use_container_width=True):
            st.session_state.question_text = eq
            st.session_state.trigger_search = True
            st.rerun()

# Evaluation Section
st.markdown("---")
st.markdown("## 📊 Evaluation & Metrics")

# Quick metrics reference (always visible)
st.markdown("""
**Quick Metrics Guide:**
- 📚 **Context Recall** - Did we retrieve the right information?
- 🎯 **Context Precision** - Did we retrieve *only* relevant information?
- ✅ **Faithfulness** - Is the answer grounded in the context?
- 💬 **Answer Relevancy** - Does the answer address the question?
- 🎓 **Answer Correctness** - Custom metric comparing to ground truth
""")

# Detailed explanation (expandable)
with st.expander("ℹ️ **Click for detailed metric explanations**", expanded=False):
    st.markdown("""
    Our RAG system is evaluated using two approaches: **Custom LLM-as-a-Judge** and **RAGAS Framework**.  
    Here's what each metric measures:
    
    ### 🎯 **Core Evaluation Concepts**
    
    #### 📚 **Context Recall** (Did we retrieve the right information?)
    - Measures if the system found **all relevant chunks** from the document
    - **High score (>0.9):** System retrieved everything needed to answer
    - **Low score (<0.7):** System missed important information
    - **Analogy:** Like a student finding all relevant pages in a textbook
    
    #### 🎯 **Context Precision** (Did we retrieve *only* relevant information?)
    - Measures if the retrieved chunks are **actually relevant** to the question
    - **High score (>0.9):** No noise, all chunks are useful
    - **Low score (<0.7):** Retrieved irrelevant/distracting information
    - **Analogy:** Like a student not getting distracted by unrelated chapters
    
    #### ✅ **Faithfulness** (Is the answer grounded in the context?)
    - Measures if the answer is **100% based on retrieved chunks** (no hallucination)
    - **High score (>0.9):** Answer uses only facts from the document
    - **Low score (<0.7):** Answer includes made-up or external information
    - **Analogy:** Like a student citing only the textbook, not making things up
    
    #### 💬 **Answer Relevancy** (Does the answer address the question?)
    - Measures if the answer is **directly relevant** to what was asked
    - **High score (>0.9):** Answer is on-topic and complete
    - **Low score (<0.7):** Answer is vague, off-topic, or incomplete
    - **Analogy:** Like a student answering exactly what the teacher asked
    
    #### 🎓 **Answer Correctness** (Custom metric)
    - Compares system answer to **ground truth** (expected answer)
    - Measures factual accuracy and completeness
    
    ---
    
    ### 🔍 **Why Two Evaluation Frameworks?**
    
    | Framework | Purpose | Judge LLM | Key Focus |
    |-----------|---------|-----------|-----------|
    | **Custom (LLM-as-Judge)** | Answer correctness vs. ground truth | Gemini 2.5 Flash | Factual accuracy |
    | **RAGAS** | RAG-specific metrics | GPT-4o-mini | Retrieval quality + faithfulness |
    
    **Both frameworks use a different LLM than the RAG system (GPT-4o-mini) to prevent bias!**
    
    ---
    
    📖 *For detailed explanations, see:*  
    - `evaluation/evaluation_explained.md` (Custom LLM-as-Judge)  
    - `evaluation-ragas/evaluation-ragas-explained.md` (RAGAS Framework)
    """)

col1, col2 = st.columns(2)

with col1:
    # Create a visually separated container for LLM-as-a-Judge
    with st.container(border=True):
        st.markdown("### 🧪 LLM-as-a-Judge")
        
        try:
            # Load and display saved results automatically
            results_path = project_root / "evaluation" / "evaluation_results.json"
            if results_path.exists():
                with open(results_path, 'r') as f:
                    data = json.load(f)
                
                summary = data.get('summary', {})
                results = data.get('results', [])
                
                st.info(f"📁 {summary.get('total_cases', 0)} test cases")
                
                # Display summary metrics with color coding (2x2 grid)
                st.markdown("#### 📈 Summary Metrics")
                
                # First row: Correct and Relevant
                row1_col1, row1_col2 = st.columns(2)
                with row1_col1:
                    correctness = summary.get('avg_answer_correctness', 0)
                    st.metric(
                        "✅ Correct", 
                        f"{correctness:.2f}",
                        delta="Excellent" if correctness >= 0.9 else "Good" if correctness >= 0.7 else "Needs Work"
                    )
                
                with row1_col2:
                    relevancy = summary.get('avg_context_relevancy', 0)
                    st.metric(
                        "🎯 Relevant", 
                        f"{relevancy:.2f}",
                        delta="Excellent" if relevancy >= 0.9 else "Good" if relevancy >= 0.7 else "Needs Work"
                    )
                
                # Second row: Recall and Final
                row2_col1, row2_col2 = st.columns(2)
                with row2_col1:
                    recall = summary.get('avg_context_recall', 0)
                    st.metric(
                        "📚 Recall", 
                        f"{recall:.2f}",
                        delta="Excellent" if recall >= 0.9 else "Good" if recall >= 0.7 else "Needs Work"
                    )
                
                with row2_col2:
                    final_score = summary.get('avg_final_score', 0)
                    st.metric(
                        "🏆 Final", 
                        f"{final_score:.2f}",
                        delta="Excellent" if final_score >= 0.9 else "Good" if final_score >= 0.7 else "Needs Work"
                    )
                
                # Show per-question breakdown
                with st.expander("📋 Per-Question Results"):
                    for result in results:
                        q_id = result.get('question_id', 'Unknown')
                        question = result.get('question', 'N/A')
                        
                        st.markdown(f"**{q_id}:** {question}")
                        
                        # Extract scores from nested objects
                        answer_score = result.get('answer_correctness', {}).get('score', 0)
                        context_rel_score = result.get('context_relevancy', {}).get('score', 0)
                        context_rec_score = result.get('context_recall', {}).get('score', 0)
                        final = result.get('final_score', 0)
                        
                        result_col1, result_col2, result_col3, result_col4 = st.columns(4)
                        with result_col1:
                            st.write(f"✅ Answer: {answer_score:.2f}")
                        with result_col2:
                            st.write(f"🎯 Relevancy: {context_rel_score:.2f}")
                        with result_col3:
                            st.write(f"📚 Recall: {context_rec_score:.2f}")
                        with result_col4:
                            st.write(f"🏆 Final: {final:.2f}")
                        
                        # Show explanations in sub-expander
                        with st.expander(f"📝 View explanations for {q_id}"):
                            st.markdown("**Answer Correctness:**")
                            st.write(result.get('answer_correctness', {}).get('explanation', 'N/A'))
                            st.markdown("**Context Relevancy:**")
                            st.write(result.get('context_relevancy', {}).get('explanation', 'N/A'))
                            st.markdown("**Context Recall:**")
                            st.write(result.get('context_recall', {}).get('explanation', 'N/A'))
                        
                        st.markdown("---")
            
                # Show full summary JSON
                with st.expander("📄 View Full Summary JSON"):
                    st.json(summary)
            else:
                st.warning("⚠️ No saved results found. Run evaluation first: `python evaluation/run_evaluation.py`")
                
        except Exception as e:
            st.error(f"❌ Error loading results: {e}")
            st.exception(e)

with col2:
    # Create a visually separated container for RAGAS
    with st.container(border=True):
        st.markdown("### 🎯 RAGAS Evaluation")
        
        try:
            # Load and display saved results automatically
            results_path = project_root / "evaluation-ragas" / "ragas_results.json"
            if results_path.exists():
                with open(results_path, 'r') as f:
                    data = json.load(f)
                
                summary = data.get('summary', {})
                results = data.get('results', [])
                
                st.info(f"📁 {summary.get('total_cases', 0)} test cases")
                
                # Display summary metrics with color coding (2x2 grid)
                st.markdown("#### 📈 RAGAS Metrics")
                
                # First row: Recall and Precision
                row1_col1, row1_col2 = st.columns(2)
                with row1_col1:
                    recall = summary.get('avg_context_recall', 0)
                    st.metric(
                        "📚 Recall", 
                        f"{recall:.2f}",
                        delta="Excellent" if recall >= 0.9 else "Good" if recall >= 0.7 else "Needs Work"
                    )
                
                with row1_col2:
                    precision = summary.get('avg_context_precision', 0)
                    st.metric(
                        "🎯 Precision", 
                        f"{precision:.2f}",
                        delta="Excellent" if precision >= 0.9 else "Good" if precision >= 0.7 else "Needs Work"
                    )
                
                # Second row: Faithfulness and Relevancy
                row2_col1, row2_col2 = st.columns(2)
                with row2_col1:
                    faithfulness = summary.get('avg_faithfulness', 0)
                    st.metric(
                        "✅ Faithful", 
                        f"{faithfulness:.2f}",
                        delta="Excellent" if faithfulness >= 0.9 else "Good" if faithfulness >= 0.7 else "Needs Work"
                    )
                
                with row2_col2:
                    relevancy = summary.get('avg_answer_relevancy', 0)
                    st.metric(
                        "💬 Relevant", 
                        f"{relevancy:.2f}",
                        delta="Excellent" if relevancy >= 0.9 else "Good" if relevancy >= 0.7 else "Needs Work"
                    )
                
                # Show per-question breakdown
                with st.expander("📋 Per-Question Results"):
                    for result in results:
                        q_id = result.get('question_id', 'Unknown')
                        question = result.get('question', 'N/A')
                        
                        st.markdown(f"**{q_id}:** {question}")
                        
                        result_col1, result_col2, result_col3, result_col4 = st.columns(4)
                        with result_col1:
                            recall_val = result.get('context_recall')
                            st.write(f"Recall: {recall_val:.2f}" if recall_val is not None else "Recall: N/A")
                        with result_col2:
                            precision_val = result.get('context_precision')
                            st.write(f"Precision: {precision_val:.2f}" if precision_val is not None else "Precision: N/A")
                        with result_col3:
                            faith_val = result.get('faithfulness')
                            st.write(f"Faith: {faith_val:.2f}" if faith_val is not None else "Faith: N/A")
                        with result_col4:
                            rel_val = result.get('answer_relevancy')
                            st.write(f"Relevancy: {rel_val:.2f}" if rel_val is not None else "Relevancy: N/A")
                        
                        st.markdown("---")
            
                # Show full summary JSON
                with st.expander("📄 View Full Summary JSON"):
                    st.json(summary)
            else:
                st.warning("⚠️ No saved results found. Run RAGAS evaluation first: `python evaluation-ragas/ragas_eval.py`")
                
        except Exception as e:
            st.error(f"❌ Error loading results: {e}")
            st.exception(e)

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray; font-size: 0.9em;'>
    🚗 Auto Claims Q&A System | Powered by RAG | Evaluation-Ready
    </div>
    """,
    unsafe_allow_html=True
)
