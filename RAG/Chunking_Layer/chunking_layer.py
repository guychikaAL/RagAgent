"""
====================================================
CHUNKING LAYER
====================================================

RESPONSIBILITY:
This layer ONLY transforms ONE CLAIM DOCUMENT into hierarchical Nodes.

NO embeddings.
NO vector stores.
NO retrieval.
NO agents.

INPUT:
- ONE LlamaIndex Document representing a SINGLE CLAIM
  (from Claim Segmentation Layer)

OUTPUT:
- List[BaseNode] with hierarchical structure (claim-scoped):
  Claim Document → Sections → Parent Chunks → Child Chunks

WHY THIS EXISTS:
- Each claim is an independent business entity
- Hierarchical chunking enables both precision (child chunks) and context (parent chunks)
- Supports AutoMergingRetriever and RecursiveRetriever
- Separates structure creation from embedding/indexing
- Enables deterministic, explainable chunking PER CLAIM

WHY SINGLE-CLAIM PROCESSING:
- Prevents mixing facts across different claims
- Each claim has its own complete hierarchy
- Enables claim-specific retrieval and filtering
- No cross-claim assumptions or dependencies

WHY LLAMAINDEX ONLY:
- TextNode and IndexNode are LlamaIndex primitives
- NodeRelationship enables hierarchical navigation
- Integrates seamlessly with LlamaIndex indexes

CRITICAL: This layer does NOT create embeddings.
Embedding configuration is defined in the Index Layer.
All chunk text must be FINAL and deterministic here.
All nodes MUST include claim_id in metadata.
"""

import re
import hashlib
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

from llama_index.core import Document
from llama_index.core.schema import TextNode, IndexNode, BaseNode, NodeRelationship, RelatedNodeInfo


@dataclass
class Section:
    """
    Represents a logical section of the document.
    
    WHY: Sections provide the top level of hierarchy.
    They enable context-aware retrieval within document structure.
    """
    title: str
    text: str
    start_char: int
    end_char: int
    position_index: int


class ChunkingPipeline:
    """
    Production-grade hierarchical chunking pipeline for SINGLE CLAIMS.
    
    Transforms ONE CLAIM DOCUMENT into a 3-level hierarchy:
    - Sections (logical divisions within the claim)
    - Parent chunks (250-600 tokens, semantic units)
    - Child chunks (80-150 tokens, atomic facts)
    
    WHY SINGLE-CLAIM SCOPE:
    - Input is ONE claim from Claim Segmentation Layer
    - All nodes belong to the SAME claim
    - Prevents mixing facts from different claims
    - Each claim gets independent hierarchical structure
    
    WHY HIERARCHICAL:
    - Child chunks: High precision for needle-in-haystack queries
    - Parent chunks: High context for summary queries
    - Sections: Claim structure for context
    
    WHY NO EMBEDDINGS:
    - Embeddings are expensive and belong in the Index Layer
    - Chunking is about structure, not vectors
    - Embedding configuration must be consistent across all layers
    """
    
    def __init__(
        self,
        parent_chunk_size: int = 400,
        parent_chunk_overlap: int = 50,
        child_chunk_size: int = 120,
        child_chunk_overlap: int = 20,
    ):
        """
        Initialize the chunking pipeline.
        
        Args:
            parent_chunk_size: Target tokens for parent chunks (default 400)
            parent_chunk_overlap: Overlap tokens for parent chunks (default 50)
            child_chunk_size: Target tokens for child chunks (default 120)
            child_chunk_overlap: Overlap tokens for child chunks (default 20)
            
        WHY THESE DEFAULTS:
        - Parent 400 tokens ≈ 1-2 paragraphs, good semantic unit
        - Child 120 tokens ≈ 1-3 sentences, good atomic fact unit
        - Overlaps preserve context across boundaries
        """
        self.parent_chunk_size = parent_chunk_size
        self.parent_chunk_overlap = parent_chunk_overlap
        self.child_chunk_size = child_chunk_size
        self.child_chunk_overlap = child_chunk_overlap
        
        # Simple token estimation: ~4 chars per token (English average)
        # WHY: Avoids expensive tokenizer calls during chunking
        # This is approximate but sufficient for chunking boundaries
        self.chars_per_token = 4
    
    def build_nodes(self, claim_document: Document) -> List[BaseNode]:
        """
        Build hierarchical nodes from ONE CLAIM DOCUMENT.
        
        This is the main entry point for this layer.
        
        Args:
            claim_document: LlamaIndex Document representing ONE CLAIM
                           (from Claim Segmentation Layer)
                           Expected metadata: claim_id, claim_number, claim_index
            
        Returns:
            List of BaseNode objects with hierarchical relationships
            All nodes will include claim_id in metadata
            
        WHY LIST[BASENODE]:
        - LlamaIndex index constructors expect List[BaseNode]
        - Contains mix of IndexNode (sections) and TextNode (chunks)
        - Preserves all hierarchical relationships
        - All nodes scoped to this ONE claim
        """
        # Extract claim_id from document metadata
        # WHY: All nodes must carry claim_id for filtering
        claim_id = claim_document.metadata.get('claim_id', claim_document.doc_id)
        claim_number = claim_document.metadata.get('claim_number', 'unknown')
        
        # Stage 1: Detect sections WITHIN THIS CLAIM
        # WHY: Sections provide logical structure within the claim
        sections = self._detect_sections(claim_document)
        
        # Stage 2-5: Build hierarchy
        # WHY: Each stage has a clear responsibility
        all_nodes = []
        
        for section_idx, section in enumerate(sections):
            # Create section node (claim-scoped)
            section_node = self._create_section_node(
                section=section,
                document=claim_document,
                claim_id=claim_id,
                claim_number=claim_number
            )
            all_nodes.append(section_node)
            
            # Build parent chunks for this section (claim-scoped)
            parent_nodes = self._build_parent_chunks(
                section=section,
                section_node=section_node,
                document=claim_document,
                claim_id=claim_id,
                claim_number=claim_number
            )
            
            # Build child chunks for each parent (claim-scoped)
            for parent_node in parent_nodes:
                child_nodes = self._build_child_chunks(
                    parent_node=parent_node,
                    section_node=section_node,
                    document=claim_document,
                    claim_id=claim_id,
                    claim_number=claim_number
                )
                
                # Link parent to children
                parent_node.relationships[NodeRelationship.CHILD] = [
                    RelatedNodeInfo(node_id=child.node_id)
                    for child in child_nodes
                ]
                
                all_nodes.extend(child_nodes)
            
            # Link section to parents
            section_node.relationships[NodeRelationship.CHILD] = [
                RelatedNodeInfo(node_id=parent.node_id)
                for parent in parent_nodes
            ]
            
            all_nodes.extend(parent_nodes)
        
        # Stage 6: Clean and validate
        # WHY: Remove empty/invalid chunks, ensure deterministic output
        all_nodes = self._clean_and_validate_nodes(all_nodes)
        
        return all_nodes
    
    def _detect_sections(self, document: Document) -> List[Section]:
        """
        Stage 1: Section Detection
        
        Detects logical sections in the document using:
        - Keywords like "SECTION", "PART", "CHAPTER"
        - ALL CAPS headings
        - Numbered headings (1., 2., etc.)
        
        WHY THIS STAGE:
        - Documents often have logical structure
        - Sections provide context boundaries
        - Enables section-aware retrieval
        
        WHY HEURISTIC:
        - PDF structure is lost after text extraction
        - Must infer from text patterns
        - Better than no structure at all
        
        Args:
            document: Input document
            
        Returns:
            List of Section objects (always at least 1)
        """
        text = document.text
        
        # Safety check: empty document
        if not text or not text.strip():
            return [Section(
                title="Empty Document",
                text="",
                start_char=0,
                end_char=0,
                position_index=0
            )]
        
        # Pattern 1: SECTION keywords
        # Matches: "SECTION 1", "SECTION A", "SECTION 1 –", etc.
        section_pattern = r'SECTION\s+[A-Z0-9]+[^\n]*'
        
        # Find all potential section markers
        lines = text.split('\n')
        section_markers = []
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            # Skip empty lines
            if not line_stripped:
                continue
            
            # Check for SECTION keyword (case-insensitive for robustness)
            if re.search(section_pattern, line_stripped, re.IGNORECASE):
                section_markers.append((i, line_stripped, 'section'))
            # Check for ALL CAPS heading (short, < 80 chars, multiple words)
            elif (len(line_stripped) < 80 and 
                  line_stripped.isupper() and 
                  len(line_stripped.split()) >= 2 and
                  len(line_stripped.split()) <= 12 and
                  not line_stripped.endswith(('.', ',', ';'))):  # Not a sentence
                section_markers.append((i, line_stripped, 'caps'))
        
        # If we found section markers, use them
        if section_markers:
            sections = []
            
            for idx, (line_num, title, marker_type) in enumerate(section_markers):
                # Find start and end positions in original text
                # WHY: We need character positions for metadata
                start_pos = self._find_line_position(text, line_num)
                
                # End position is at next section or end of document
                if idx + 1 < len(section_markers):
                    next_line_num = section_markers[idx + 1][0]
                    end_pos = self._find_line_position(text, next_line_num)
                else:
                    end_pos = len(text)
                
                section_text = text[start_pos:end_pos].strip()
                
                # Only add if section has content
                if section_text:
                    sections.append(Section(
                        title=title,
                        text=section_text,
                        start_char=start_pos,
                        end_char=end_pos,
                        position_index=idx
                    ))
            
            # If we found valid sections, return them
            if sections:
                return sections
        
        # No sections found: create one default section
        # WHY: Always have at least one section for consistent structure
        # This ensures we never return an empty list
        return [Section(
            title="Document",
            text=text.strip(),
            start_char=0,
            end_char=len(text),
            position_index=0
        )]
    
    def _find_line_position(self, text: str, line_num: int) -> int:
        """
        Find character position of a line number in text.
        
        WHY: We need char positions for section boundaries.
        """
        lines = text.split('\n')
        pos = 0
        for i in range(min(line_num, len(lines))):
            pos += len(lines[i]) + 1  # +1 for newline
        return pos
    
    def _create_section_node(
        self, 
        section: Section, 
        document: Document,
        claim_id: str,
        claim_number: str
    ) -> IndexNode:
        """
        Create an IndexNode for a section.
        
        WHY INDEXNODE:
        - IndexNode is a container/organizational node
        - Does not contain full text (just references)
        - Used by RecursiveRetriever and AutoMergingRetriever
        
        Args:
            section: Section object
            document: Original document
            
        Returns:
            IndexNode with section metadata
        """
        # Generate deterministic section ID
        # WHY: Same section should get same ID across runs
        section_id = self._generate_id(f"section_{document.doc_id}_{section.position_index}")
        
        # Calculate token length
        token_length = self._estimate_tokens(section.text)
        
        # Create IndexNode
        # WHY: Sections are organizational, not retrieval targets themselves
        node = IndexNode(
            text=section.title,  # Just the title, not full text
            index_id=section_id,
            metadata={
                "section_id": section_id,
                "title": section.title,
                "position_index": section.position_index,
                "start_char_index": section.start_char,
                "end_char_index": section.end_char,
                "token_length": token_length,
                "node_type": "section",
                # Claim-specific metadata (CRITICAL)
                "claim_id": claim_id,
                "claim_number": claim_number,
                # Carry over document-level metadata
                "document_id": document.doc_id,
                "document_type": document.metadata.get("document_type", "unknown"),
                "source_type": document.metadata.get("source_type", "unknown"),
            }
        )
        
        # Set node ID
        node.node_id = section_id
        
        return node
    
    def _build_parent_chunks(
        self,
        section: Section,
        section_node: IndexNode,
        document: Document,
        claim_id: str,
        claim_number: str
    ) -> List[TextNode]:
        """
        Stage 2: Parent Chunking
        
        Splits section text into parent chunks (250-600 tokens).
        
        WHY PARENT CHUNKS:
        - Provide broader context than child chunks
        - Used by Summary Retriever for high-recall queries
        - Enable AutoMergingRetriever to merge children back to parent
        
        WHY 250-600 TOKENS:
        - Large enough to contain complete thoughts/paragraphs
        - Small enough to be semantically focused
        - Fits comfortably in LLM context windows
        
        Args:
            section: Section to chunk
            section_node: Section's IndexNode
            document: Original document
            
        Returns:
            List of TextNode objects (parent chunks)
        """
        text = section.text
        
        # Split by paragraphs first
        # WHY: Paragraphs are natural semantic boundaries
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        parent_chunks = []
        current_chunk = []
        current_size = 0
        position_index = 0
        
        for para in paragraphs:
            para_tokens = self._estimate_tokens(para)
            
            # If this paragraph alone exceeds max size, split it
            if para_tokens > self.parent_chunk_size:
                # Flush current chunk first
                if current_chunk:
                    chunk_text = '\n\n'.join(current_chunk)
                    parent_chunks.append((chunk_text, position_index))
                    position_index += 1
                    current_chunk = []
                    current_size = 0
                
                # Split large paragraph by sentences
                sentences = self._split_sentences(para)
                sent_chunk = []
                sent_size = 0
                
                for sent in sentences:
                    sent_tokens = self._estimate_tokens(sent)
                    if sent_size + sent_tokens > self.parent_chunk_size and sent_chunk:
                        # Flush sentence chunk
                        chunk_text = ' '.join(sent_chunk)
                        parent_chunks.append((chunk_text, position_index))
                        position_index += 1
                        sent_chunk = []
                        sent_size = 0
                    
                    sent_chunk.append(sent)
                    sent_size += sent_tokens
                
                # Add remaining sentences
                if sent_chunk:
                    chunk_text = ' '.join(sent_chunk)
                    parent_chunks.append((chunk_text, position_index))
                    position_index += 1
            
            # If adding this paragraph would exceed max size, flush current chunk
            elif current_size + para_tokens > self.parent_chunk_size and current_chunk:
                chunk_text = '\n\n'.join(current_chunk)
                parent_chunks.append((chunk_text, position_index))
                position_index += 1
                current_chunk = [para]
                current_size = para_tokens
            
            # Otherwise, add paragraph to current chunk
            else:
                current_chunk.append(para)
                current_size += para_tokens
        
        # Add final chunk
        if current_chunk:
            chunk_text = '\n\n'.join(current_chunk)
            parent_chunks.append((chunk_text, position_index))
        
        # Create TextNode objects for parent chunks
        parent_nodes = []
        
        for idx, (chunk_text, pos_idx) in enumerate(parent_chunks):
            node = self._create_parent_node(
                text=chunk_text,
                section=section,
                section_node=section_node,
                position_index=pos_idx,
                document=document,
                claim_id=claim_id,
                claim_number=claim_number
            )
            parent_nodes.append(node)
        
        return parent_nodes
    
    def _create_parent_node(
        self,
        text: str,
        section: Section,
        section_node: IndexNode,
        position_index: int,
        document: Document,
        claim_id: str,
        claim_number: str
    ) -> TextNode:
        """
        Create a TextNode for a parent chunk.
        
        WHY TEXTNODE:
        - TextNode contains actual text for embedding/retrieval
        - Used by both VectorStoreIndex and SummaryIndex
        
        Args:
            text: Parent chunk text
            section: Section containing this chunk
            section_node: Section's IndexNode
            position_index: Position within section
            document: Original document
            
        Returns:
            TextNode with parent chunk metadata
        """
        # Generate deterministic parent ID
        parent_id = self._generate_id(
            f"parent_{section_node.node_id}_{position_index}"
        )
        
        # Calculate token length
        token_length = self._estimate_tokens(text)
        
        # Extract semantic features
        # WHY: Helps with debugging and potential filtering
        contains_dates = bool(re.search(r'\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4}', text))
        contains_times = bool(re.search(r'\d{1,2}:\d{2}', text))
        contains_numbers = bool(re.search(r'\d+', text))
        
        # Simple topic extraction (first few words)
        words = text.split()[:5]
        semantic_topic = ' '.join(words) + ('...' if len(text.split()) > 5 else '')
        
        # Prepend claim context to parent chunk text for better semantic matching
        # WHY: Enables queries like "claim number 1" to match correctly
        # Make claim number VERY prominent for better matching
        claim_title = document.metadata.get("title", f"AUTO CLAIM FORM #{claim_number}")
        contextualized_text = f"CLAIM NUMBER: {claim_number}\n{claim_title}\n{text}"
        
        # Create TextNode
        node = TextNode(
            text=contextualized_text,
            metadata={
                "parent_id": parent_id,
                "section_id": section_node.node_id,
                "chunk_level": "parent",
                "position_index": position_index,
                "token_length": token_length,
                "semantic_topic": semantic_topic,
                "contains_dates": contains_dates,
                "contains_times": contains_times,
                "contains_numbers": contains_numbers,
                "node_type": "parent_chunk",
                # Claim-specific metadata (CRITICAL)
                "claim_id": claim_id,
                "claim_number": claim_number,
                "claimant_name": document.metadata.get("claimant_name"),  # DYNAMIC! No hardcoding!
                # Carry over document-level metadata
                "document_id": document.doc_id,
                "document_type": document.metadata.get("document_type", "unknown"),
                "source_type": document.metadata.get("source_type", "unknown"),
            }
        )
        
        # Set node ID
        node.node_id = parent_id
        
        # Link to section (parent relationship)
        # WHY: Enables upward navigation in hierarchy
        node.relationships[NodeRelationship.PARENT] = RelatedNodeInfo(
            node_id=section_node.node_id
        )
        
        return node
    
    def _build_child_chunks(
        self,
        parent_node: TextNode,
        section_node: IndexNode,
        document: Document,
        claim_id: str,
        claim_number: str
    ) -> List[TextNode]:
        """
        Stage 3: Child Chunking
        
        Splits parent chunk into child chunks (80-150 tokens).
        
        WHY CHILD CHUNKS:
        - Atomic fact units for high-precision retrieval
        - Used by Needle Retriever for specific questions
        - Small enough to be highly focused
        
        WHY 80-150 TOKENS:
        - Large enough to contain complete facts
        - Small enough to avoid ambiguity
        - Typical sentence or two
        
        WHY OVERLAP:
        - Preserves context across boundaries
        - Ensures facts aren't split awkwardly
        
        Args:
            parent_node: Parent TextNode to split
            section_node: Section containing this parent
            document: Original document
            
        Returns:
            List of TextNode objects (child chunks)
        """
        text = parent_node.text
        
        # Split into sentences first
        # WHY: Sentences are natural atomic fact boundaries
        sentences = self._split_sentences(text)
        
        child_chunks = []
        current_chunk = []
        current_size = 0
        position_index = 0
        
        for sent in sentences:
            sent_tokens = self._estimate_tokens(sent)
            
            # If adding this sentence would exceed max size, flush current chunk
            if current_size + sent_tokens > self.child_chunk_size and current_chunk:
                chunk_text = ' '.join(current_chunk)
                child_chunks.append((chunk_text, position_index))
                position_index += 1
                
                # Apply overlap: keep last sentence for context
                # WHY: Overlap preserves context across boundaries
                if len(current_chunk) > 1 and self.child_chunk_overlap > 0:
                    overlap_sent = current_chunk[-1]
                    overlap_tokens = self._estimate_tokens(overlap_sent)
                    if overlap_tokens <= self.child_chunk_overlap:
                        current_chunk = [overlap_sent, sent]
                        current_size = overlap_tokens + sent_tokens
                    else:
                        current_chunk = [sent]
                        current_size = sent_tokens
                else:
                    current_chunk = [sent]
                    current_size = sent_tokens
            
            # Otherwise, add sentence to current chunk
            else:
                current_chunk.append(sent)
                current_size += sent_tokens
        
        # Add final chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            child_chunks.append((chunk_text, position_index))
        
        # Create TextNode objects for child chunks
        child_nodes = []
        
        for idx, (chunk_text, pos_idx) in enumerate(child_chunks):
            node = self._create_child_node(
                text=chunk_text,
                parent_node=parent_node,
                section_node=section_node,
                position_index=pos_idx,
                document=document,
                claim_id=claim_id,
                claim_number=claim_number
            )
            child_nodes.append(node)
        
        return child_nodes
    
    def _create_child_node(
        self,
        text: str,
        parent_node: TextNode,
        section_node: IndexNode,
        position_index: int,
        document: Document,
        claim_id: str,
        claim_number: str
    ) -> TextNode:
        """
        Create a TextNode for a child chunk.
        
        WHY CHILD CHUNKS:
        - Atomic fact units for high-precision retrieval
        - Enable needle-in-haystack queries
        - Used with similarity threshold for precision
        
        Args:
            text: Child chunk text
            parent_node: Parent TextNode
            section_node: Section IndexNode
            position_index: Position within parent
            document: Original document
            
        Returns:
            TextNode with child chunk metadata
        """
        # Generate deterministic child ID
        child_id = self._generate_id(
            f"child_{parent_node.node_id}_{position_index}"
        )
        
        # Calculate token length
        token_length = self._estimate_tokens(text)
        
        # Prepend claim context to chunk text for better semantic matching
        # WHY: Enables queries like "claim number 1" to match correctly
        # The claim form identifier is included in the embedding
        # Make claim number VERY prominent for better matching
        claim_title = document.metadata.get("title", f"AUTO CLAIM FORM #{claim_number}")
        contextualized_text = f"CLAIM NUMBER: {claim_number}\n{claim_title}\n{text}"
        
        # Create TextNode
        node = TextNode(
            text=contextualized_text,
            metadata={
                "chunk_id": child_id,
                "parent_id": parent_node.node_id,
                "section_id": section_node.node_id,
                "chunk_level": "child",
                "position_index": position_index,
                "token_length": token_length,
                "is_atomic_facts_unit": True,  # Critical for retrieval strategy
                "node_type": "child_chunk",
                # Claim-specific metadata (CRITICAL)
                "claim_id": claim_id,
                "claim_number": claim_number,
                "claimant_name": document.metadata.get("claimant_name"),  # DYNAMIC! No hardcoding!
                # Carry over document-level metadata
                "document_id": document.doc_id,
                "document_type": document.metadata.get("document_type", "unknown"),
                "source_type": document.metadata.get("source_type", "unknown"),
            }
        )
        
        # Set node ID
        node.node_id = child_id
        
        # Link to parent (upward navigation)
        # WHY: Enables AutoMergingRetriever to fetch parent when needed
        node.relationships[NodeRelationship.PARENT] = RelatedNodeInfo(
            node_id=parent_node.node_id
        )
        
        # Link to section (for context)
        # Note: This is optional but helps with debugging
        node.relationships[NodeRelationship.SOURCE] = RelatedNodeInfo(
            node_id=section_node.node_id
        )
        
        return node
    
    def _split_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences.
        
        WHY: Sentences are natural boundaries for atomic facts.
        
        Uses simple regex-based splitting.
        Good enough for most English text.
        
        Args:
            text: Text to split
            
        Returns:
            List of sentences
        """
        # Split on sentence-ending punctuation followed by space and capital letter
        # WHY: Handles most common cases without expensive NLP
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
        
        # Clean up
        sentences = [s.strip() for s in sentences if s.strip()]
        
        return sentences
    
    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.
        
        WHY: We need token counts for chunk size boundaries.
        WHY NOT REAL TOKENIZER: Expensive and not needed for chunking.
        
        Uses heuristic: ~4 characters per token for English.
        This is approximate but sufficient for chunking.
        
        Args:
            text: Text to estimate
            
        Returns:
            Estimated token count
        """
        return max(1, len(text) // self.chars_per_token)
    
    def _generate_id(self, text: str) -> str:
        """
        Generate deterministic ID from text.
        
        WHY DETERMINISTIC:
        - Same input should produce same ID across runs
        - Enables reproducible indexing
        - Critical for production systems
        
        Args:
            text: Text to hash
            
        Returns:
            16-character hex string
        """
        return hashlib.sha256(text.encode()).hexdigest()[:16]
    
    def _clean_and_validate_nodes(self, nodes: List[BaseNode]) -> List[BaseNode]:
        """
        Stage 4: Clean and Validate
        
        Ensures all nodes are valid and ready for indexing.
        
        WHY THIS STAGE:
        - Remove empty or near-empty chunks
        - Validate required metadata
        - Ensure deterministic output
        
        Args:
            nodes: List of nodes to clean
            
        Returns:
            Cleaned and validated list of nodes
        """
        cleaned = []
        
        for node in nodes:
            # Ensure node has ID (required for all nodes)
            if not node.node_id:
                continue
            
            # For IndexNodes (sections), we only need non-empty text (title)
            # WHY: IndexNodes are organizational, they only have titles
            if isinstance(node, IndexNode):
                if node.text and node.text.strip():
                    cleaned.append(node)
                continue
            
            # For TextNodes (parents/children), validate text content
            if isinstance(node, TextNode):
                # Skip empty nodes
                if not node.text or not node.text.strip():
                    continue
                
                # Skip very short nodes (< 10 characters)
                # WHY: Too short to be useful, likely artifacts
                if len(node.text.strip()) < 10:
                    continue
                
                # Trim whitespace from text
                # WHY: Whitespace affects embeddings
                node.text = node.text.strip()
                cleaned.append(node)
                continue
            
            # For any other node type, just add it
            cleaned.append(node)
        
        return cleaned


# Production-ready factory function
def create_chunking_pipeline(
    parent_chunk_size: int = 400,
    parent_chunk_overlap: int = 50,
    child_chunk_size: int = 120,
    child_chunk_overlap: int = 20,
) -> ChunkingPipeline:
    """
    Factory function to create a configured chunking pipeline.
    
    WHY: Provides clean interface for importing and using this layer.
    
    Args:
        parent_chunk_size: Target tokens for parent chunks
        parent_chunk_overlap: Overlap tokens for parent chunks
        child_chunk_size: Target tokens for child chunks
        child_chunk_overlap: Overlap tokens for child chunks
        
    Returns:
        Configured ChunkingPipeline instance
    """
    return ChunkingPipeline(
        parent_chunk_size=parent_chunk_size,
        parent_chunk_overlap=parent_chunk_overlap,
        child_chunk_size=child_chunk_size,
        child_chunk_overlap=child_chunk_overlap,
    )

