"""
====================================================
CLAIM SEGMENTATION LAYER
====================================================

RESPONSIBILITY:
This layer ONLY segments one physical PDF into multiple logical Claims.

NO chunking.
NO nodes.
NO embeddings.
NO vector stores.
NO retrieval.

INPUT:
- One llama_index.core.Document (the full PDF)

OUTPUT:
- List[llama_index.core.Document] (one per Claim)

WHY THIS EXISTS:
- Many insurance PDFs contain multiple claims (e.g., 20 claims in one file)
- Each claim is an independent business entity
- Queries like "What is the claim amount for claim #5?" need claim-level isolation
- Without segmentation, retrieval would mix facts across different claims

WHY THIS IS NOT CHUNKING:
- Chunking splits text into semantic units for embedding
- Segmentation splits business entities for independent processing
- Each claim gets its own chunking, indexing, and retrieval

WHY BEFORE CHUNKING:
- Chunking should operate on single-claim text, not mixed claims
- Each claim needs its own hierarchical node structure
- Enables claim-specific metadata and filtering

ARCHITECTURE POSITION:
PDF Ingestion → Claim Segmentation → Chunking → Index → Agents
"""

import re
import hashlib
from typing import List, Tuple, Optional
from dataclasses import dataclass

from llama_index.core import Document


@dataclass
class ClaimBoundary:
    """
    Represents a detected claim boundary in the document.
    
    WHY: We need to track where each claim starts/ends
    to extract the correct text slice.
    """
    claim_number: str  # e.g., "1", "2", "20"
    start_char: int
    title: str


class ClaimSegmentationPipeline:
    """
    Production-grade claim segmentation pipeline.
    
    Splits a multi-claim PDF Document into separate Documents (one per claim).
    
    WHY THIS PIPELINE:
    - Insurance PDFs often contain 20+ claims in one file
    - Each claim is an independent entity with its own:
      - Claimant information
      - Incident details
      - Amounts and dates
      - Status and notes
    - Mixing claims during retrieval causes hallucinations and incorrect answers
    
    DETERMINISTIC BEHAVIOR:
    - Uses regex patterns to detect claim boundaries
    - Same input → same output (no ML, no randomness)
    - Fallback: if no boundaries detected, return 1 claim
    
    WHY NOT MACHINE LEARNING:
    - Claim boundaries follow predictable patterns
    - Regex is fast, deterministic, and explainable
    - No training data needed
    - No model drift
    """
    
    def __init__(self):
        """
        Initialize the claim segmentation pipeline.
        
        WHY NO PARAMETERS:
        - Boundary detection is deterministic
        - Patterns are hardcoded for insurance claim forms
        - Can be extended later if needed
        """
        pass
    
    def split_into_claims(self, document: Document) -> List[Document]:
        """
        Split a document into separate claim documents.
        
        This is the main entry point for this layer.
        
        Args:
            document: LlamaIndex Document from PDF Ingestion Layer
            
        Returns:
            List of Documents, one per detected claim
            
        WHY LIST[DOCUMENT]:
        - Each claim becomes an independent document
        - The Chunking Layer will process each claim separately
        - Enables claim-level indexing and retrieval
        """
        # Stage 1: Detect claim boundaries
        # WHY: We need to know where each claim starts
        boundaries = self._detect_claim_boundaries(document)
        
        # Stage 2: Create claim documents
        # WHY: Split the text and create separate Documents
        claim_documents = self._create_claim_documents(
            document=document,
            boundaries=boundaries
        )
        
        return claim_documents
    
    def _detect_claim_boundaries(self, document: Document) -> List[ClaimBoundary]:
        """
        Detect boundaries between claims in the document.
        
        WHY THIS STAGE:
        - Insurance PDFs repeat form headers for each claim
        - We need to identify where each claim starts
        - Enables extraction of claim-specific text
        
        DETECTION STRATEGY:
        1. Look for "AUTO CLAIM FORM #N" patterns
        2. Look for "Claim Number:" or "Claim ID:" patterns
        3. Look for form numbering resets
        4. Use first occurrence as start of first claim
        
        Args:
            document: Input document with full PDF text
            
        Returns:
            List of ClaimBoundary objects (sorted by position)
        """
        text = document.text
        boundaries = []
        
        # Pattern 1: "AUTO CLAIM FORM #N"
        # Matches: "AUTO CLAIM FORM #1", "AUTO CLAIM FORM #20", etc.
        # WHY: This is the primary form header that repeats for each claim
        pattern1 = r'AUTO\s+CLAIM\s+FORM\s+#(\d+)'
        
        for match in re.finditer(pattern1, text, re.IGNORECASE):
            claim_number = match.group(1)
            start_pos = match.start()
            title = match.group(0)
            
            boundaries.append(ClaimBoundary(
                claim_number=claim_number,
                start_char=start_pos,
                title=title
            ))
        
        # Pattern 2: "Claim Number: XXXXX" (fallback)
        # WHY: Some forms may not have the header but have claim number field
        if not boundaries:
            pattern2 = r'Claim\s+Number:\s*([A-Z0-9]+)'
            
            for match in re.finditer(pattern2, text, re.IGNORECASE):
                claim_number = match.group(1)
                start_pos = match.start()
                title = f"Claim {claim_number}"
                
                boundaries.append(ClaimBoundary(
                    claim_number=claim_number,
                    start_char=start_pos,
                    title=title
                ))
        
        # Pattern 3: "SECTION 1 – CLAIMANT INFORMATION" at document start
        # WHY: If there's a structured section at the start, it's likely a claim
        if not boundaries:
            pattern3 = r'^SECTION\s+1\s*[–-]\s*CLAIMANT\s+INFORMATION'
            
            match = re.search(pattern3, text, re.IGNORECASE | re.MULTILINE)
            if match:
                boundaries.append(ClaimBoundary(
                    claim_number="1",
                    start_char=0,
                    title="Claim Form"
                ))
        
        # Sort boundaries by position
        # WHY: Ensure claims are in document order
        boundaries.sort(key=lambda b: b.start_char)
        
        # Remove duplicates (same position)
        # WHY: Multiple patterns may match the same claim boundary
        unique_boundaries = []
        last_pos = None
        for boundary in boundaries:
            # Consider boundaries within 50 chars as duplicates
            # WHY: Patterns may match slightly different positions for same claim
            if last_pos is None or boundary.start_char - last_pos > 50:
                unique_boundaries.append(boundary)
                last_pos = boundary.start_char
        
        return unique_boundaries
    
    def _create_claim_documents(
        self,
        document: Document,
        boundaries: List[ClaimBoundary]
    ) -> List[Document]:
        """
        Create separate Document objects for each claim.
        
        WHY THIS STAGE:
        - Convert boundaries into actual Documents
        - Extract text slice for each claim
        - Set claim-specific metadata
        
        Args:
            document: Original full PDF document
            boundaries: Detected claim boundaries
            
        Returns:
            List of Documents, one per claim
        """
        # If no boundaries detected, return the whole document as one claim
        # WHY: Fallback behavior - some PDFs may have only one claim
        if not boundaries:
            return [self._create_single_claim_document(
                document=document,
                claim_index=0,
                claim_text=document.text,
                title="Claim Form"
            )]
        
        claim_documents = []
        text = document.text
        
        for i, boundary in enumerate(boundaries):
            # Determine start and end positions
            start_pos = boundary.start_char
            
            # End position is at next boundary or end of document
            if i + 1 < len(boundaries):
                end_pos = boundaries[i + 1].start_char
            else:
                end_pos = len(text)
            
            # Extract claim text
            claim_text = text[start_pos:end_pos].strip()
            
            # Skip empty claims
            # WHY: May occur due to incorrect boundary detection
            if not claim_text:
                continue
            
            # Create claim document
            claim_doc = self._create_single_claim_document(
                document=document,
                claim_index=i,
                claim_text=claim_text,
                title=boundary.title,
                claim_number=boundary.claim_number
            )
            
            claim_documents.append(claim_doc)
        
        return claim_documents
    
    def _extract_claimant_name(self, claim_text: str) -> Optional[str]:
        """
        Extract claimant name from claim text DYNAMICALLY (no hardcoding!).
        
        WHY: Enables filtering by claimant name (e.g., "What is Jon Mor's phone?")
        
        Patterns matched:
        - "Name: John Doe Account" -> extracts "John Doe"
        - Works with OR WITHOUT newlines (PDF parsing may remove them!)
        - Stops before next field (like "Account Number:")
        
        Returns: Claimant name as string or None if not found
        """
        first_section = claim_text[:500]
        
        # Pattern: "Name:" followed by 2 capitalized words, then space and next field
        # WHY: PDF may remove newlines, so we stop at the next field keyword
        # Matches: "Name: Jon Mor Account" -> "Jon Mor"
        match = re.search(
            r'Name:\s*([A-Z][a-z]+\s+[A-Z][a-z]+)(?:\s+(?:Account|Address|Phone|Email|Date|Location))',
            first_section
        )
        if match:
            return match.group(1).strip()
        
        # Fallback: 3-word names (FirstName MiddleName LastName)
        match = re.search(
            r'Name:\s*([A-Z][a-z]+\s+[A-Z][a-z]+\s+[A-Z][a-z]+)(?:\s+(?:Account|Address|Phone|Email|Date|Location))',
            first_section
        )
        if match:
            return match.group(1).strip()
        
        # Fallback with newline (in case some PDFs preserve them)
        match = re.search(r'Name:\s*([A-Z][a-z]+\s+[A-Z][a-z]+)(?:\s*[\n\r])', first_section, re.MULTILINE)
        if match:
            return match.group(1).strip()
        
        return None
    
    def _create_single_claim_document(
        self,
        document: Document,
        claim_index: int,
        claim_text: str,
        title: str,
        claim_number: str = None
    ) -> Document:
        """
        Create a single claim Document with metadata.
        
        WHY: Each claim needs its own Document object with claim-specific metadata.
        CRITICAL: Extracts claimant name DYNAMICALLY (NO HARDCODING!)
        
        Args:
            document: Original full PDF document
            claim_index: 0-based index of this claim in the PDF
            claim_text: Text content for this claim only
            title: Title/header for this claim
            claim_number: Claim number from the form (if detected)
            
        Returns:
            Document object for this claim
        """
        # Generate deterministic claim_id
        # WHY: Same claim in same PDF should get same ID across runs
        # STRATEGY: Hash parent doc_id + claim_index
        claim_id_string = f"{document.doc_id}_claim_{claim_index}"
        claim_id = hashlib.sha256(claim_id_string.encode()).hexdigest()[:16]
        
        # If no claim_number detected, use index
        if not claim_number:
            claim_number = str(claim_index + 1)
        
        # Extract claimant name dynamically from claim text
        # WHY: No hardcoding! Name comes from document itself
        claimant_name = self._extract_claimant_name(claim_text)
        
        # Build metadata
        # WHY: Carry over parent metadata and add claim-specific fields
        metadata = {
            # Claim-specific metadata
            "claim_id": claim_id,
            "claim_number": claim_number,
            "claim_index": claim_index,
            "claimant_name": claimant_name,  # DYNAMIC! Extracted from document!
            "title": title,
            "source_type": "insurance_claim",
            
            # Parent document metadata
            "parent_document_id": document.doc_id,
            "parent_pdf_id": document.doc_id,
            
            # Inherited metadata from parent
            "document_type": document.metadata.get("document_type", "unknown"),
            "source_file": document.metadata.get("source_file", "unknown"),
            "language": document.metadata.get("language", "en"),
            
            # Statistics
            "claim_total_characters": len(claim_text),
            "claim_total_words": len(claim_text.split()),
        }
        
        # Create Document
        # WHY: LlamaIndex Document is the standard format
        claim_doc = Document(
            text=claim_text,
            metadata=metadata,
            doc_id=claim_id
        )
        
        return claim_doc


# Production-ready factory function
def create_claim_segmentation_pipeline() -> ClaimSegmentationPipeline:
    """
    Factory function to create a claim segmentation pipeline.
    
    WHY: Provides clean interface for importing and using this layer.
    
    Returns:
        Configured ClaimSegmentationPipeline instance
    """
    return ClaimSegmentationPipeline()

