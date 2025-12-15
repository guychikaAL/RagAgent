"""
====================================================
PDF INGESTION LAYER
====================================================

RESPONSIBILITY:
This layer ONLY ingests PDF files and produces clean LlamaIndex Documents.

NO chunking.
NO embeddings.
NO vector stores.
NO retrieval.
NO agents.

OUTPUT:
- A single llama_index.core.Document object
- With clean, normalized text
- With lightweight ingestion-level metadata

WHY THIS EXISTS:
- Separation of concerns: ingestion != chunking != indexing
- Allows independent testing of PDF extraction quality
- Enables document-level metadata that survives chunking
- Provides clean input for hierarchical chunking layer

WHY LLAMAINDEX DOCUMENT:
- Standard format for downstream LlamaIndex processing
- Carries metadata through the pipeline
- Compatible with LlamaIndex node creation

METADATA PHILOSOPHY:
- We extract ONLY ingestion-level metadata here
- The chunking layer will ENRICH this with chunk-level metadata
- Keep it simple, deterministic, and lightweight
"""

import os
import re
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import pypdf
from llama_index.core import Document


class PDFIngestionError(Exception):
    """Base exception for PDF ingestion failures."""
    pass


class PDFIngestionPipeline:
    """
    Production-grade PDF ingestion pipeline.
    
    Converts PDF files into clean LlamaIndex Documents with metadata.
    
    Pipeline stages:
    1. PDF Acquisition - validate file
    2. PDF Parsing - extract raw text
    3. Document Normalization - clean and normalize text
    4. Metadata Extraction - extract lightweight metadata
    5. Document Creation - create LlamaIndex Document
    """
    
    def __init__(self, document_type: str = "pdf_document"):
        """
        Initialize the ingestion pipeline.
        
        Args:
            document_type: Type label for the document (e.g., "insurance_claim_pdf")
                          This will be stored in metadata for downstream routing
        """
        self.document_type = document_type
    
    def ingest(self, pdf_path: str) -> Document:
        """
        Ingest a PDF file and return a clean LlamaIndex Document.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            llama_index.core.Document with clean text and metadata
            
        Raises:
            PDFIngestionError: If any stage of ingestion fails
        """
        # Stage 1: Acquire and validate PDF
        pdf_path = self._acquire_pdf(pdf_path)
        
        # Stage 2: Parse PDF and extract raw text
        raw_text, page_count = self._parse_pdf(pdf_path)
        
        # Stage 3: Normalize text (cleanup, paragraph reconstruction)
        clean_text = self._normalize_text(raw_text)
        
        # Stage 4: Extract lightweight metadata
        metadata = self._extract_metadata(
            pdf_path=pdf_path,
            clean_text=clean_text,
            page_count=page_count
        )
        
        # Stage 5: Create LlamaIndex Document
        # WHY: This is the standard format for LlamaIndex pipelines
        # The Document carries metadata through chunking and indexing
        document = Document(
            text=clean_text,
            metadata=metadata,
            # Use deterministic doc_id based on file content
            # WHY: Ensures same document gets same ID across runs
            doc_id=metadata["document_id"]
        )
        
        return document
    
    def _acquire_pdf(self, pdf_path: str) -> Path:
        """
        Stage 1: PDF Acquisition
        
        Validates that the PDF file exists and is readable.
        
        WHY THIS STAGE EXISTS:
        - Fail fast with clear error messages
        - Validate input before expensive processing
        - Prevent downstream errors with bad inputs
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Validated Path object
            
        Raises:
            PDFIngestionError: If file is invalid
        """
        path = Path(pdf_path)
        
        # Check 1: File exists
        if not path.exists():
            raise PDFIngestionError(f"PDF file does not exist: {pdf_path}")
        
        # Check 2: Is a file (not a directory)
        if not path.is_file():
            raise PDFIngestionError(f"Path is not a file: {pdf_path}")
        
        # Check 3: Has .pdf extension
        if path.suffix.lower() != ".pdf":
            raise PDFIngestionError(f"File is not a PDF: {pdf_path}")
        
        # Check 4: File is readable
        if not os.access(path, os.R_OK):
            raise PDFIngestionError(f"PDF file is not readable: {pdf_path}")
        
        # Check 5: File has non-zero size
        if path.stat().st_size == 0:
            raise PDFIngestionError(f"PDF file is empty: {pdf_path}")
        
        # Check 6: File size is reasonable (< 100MB for production safety)
        max_size_mb = 100
        size_mb = path.stat().st_size / (1024 * 1024)
        if size_mb > max_size_mb:
            raise PDFIngestionError(
                f"PDF file too large ({size_mb:.1f}MB > {max_size_mb}MB): {pdf_path}"
            )
        
        return path
    
    def _parse_pdf(self, pdf_path: Path) -> Tuple[str, int]:
        """
        Stage 2: PDF Parsing
        
        Extracts raw text from all pages of the PDF.
        
        WHY THIS STAGE EXISTS:
        - Centralize PDF parsing logic
        - Handle multi-page documents correctly
        - Apply basic cleanup (headers, footers, page numbers)
        - Detect encrypted PDFs early
        
        Args:
            pdf_path: Validated path to PDF
            
        Returns:
            Tuple of (raw_text, page_count)
            
        Raises:
            PDFIngestionError: If PDF cannot be parsed
        """
        try:
            # Open PDF with pypdf
            # WHY pypdf: Lightweight, pure Python, handles most PDFs well
            with open(pdf_path, "rb") as f:
                pdf_reader = pypdf.PdfReader(f)
                
                # Check for encryption
                if pdf_reader.is_encrypted:
                    raise PDFIngestionError(
                        f"PDF is encrypted and cannot be read: {pdf_path}"
                    )
                
                page_count = len(pdf_reader.pages)
                
                if page_count == 0:
                    raise PDFIngestionError(f"PDF has no pages: {pdf_path}")
                
                # Extract text from all pages
                # WHY: We need the full document text for hierarchical chunking
                pages_text = []
                for page_num, page in enumerate(pdf_reader.pages, start=1):
                    try:
                        page_text = page.extract_text()
                        
                        # Basic cleanup: remove page numbers at start/end of page
                        # WHY: Page numbers are artifacts, not content
                        page_text = self._remove_page_numbers(page_text, page_num)
                        
                        # Basic cleanup: fix broken line breaks
                        # WHY: PDFs often break words/lines incorrectly
                        page_text = self._fix_line_breaks(page_text)
                        
                        pages_text.append(page_text)
                        
                    except Exception as e:
                        # If one page fails, continue but log it
                        # WHY: Some pages may be corrupted but others are fine
                        print(f"Warning: Could not extract text from page {page_num}: {e}")
                        pages_text.append("")
                
                # Join all pages with double newline
                # WHY: Preserve page boundaries for potential later use
                raw_text = "\n\n".join(pages_text)
                
                # Check if we got any text
                if not raw_text.strip():
                    raise PDFIngestionError(
                        f"PDF contains no extractable text (may need OCR): {pdf_path}"
                    )
                
                return raw_text, page_count
                
        except pypdf.errors.PdfReadError as e:
            raise PDFIngestionError(f"Failed to read PDF: {e}")
        except Exception as e:
            raise PDFIngestionError(f"Unexpected error parsing PDF: {e}")
    
    def _remove_page_numbers(self, text: str, page_num: int) -> str:
        """
        Remove common page number patterns from text.
        
        WHY: Page numbers are PDF artifacts, not document content.
        They interfere with semantic understanding.
        """
        # Remove standalone numbers at start of text
        text = re.sub(r'^\s*\d+\s*\n', '', text)
        
        # Remove standalone numbers at end of text
        text = re.sub(r'\n\s*\d+\s*$', '', text)
        
        # Remove "Page N" patterns
        text = re.sub(r'\bPage\s+\d+\b', '', text, flags=re.IGNORECASE)
        
        return text
    
    def _fix_line_breaks(self, text: str) -> str:
        """
        Fix broken line breaks and de-hyphenate words.
        
        WHY: PDFs often break lines in the middle of words or sentences.
        This makes the text hard to read and chunk properly.
        
        APPROACH:
        - If a line ends with a hyphen, join with next line
        - If a line ends mid-word (lowercase), join with next line
        - If a line ends with punctuation, keep the break
        """
        lines = text.split('\n')
        fixed_lines = []
        
        i = 0
        while i < len(lines):
            line = lines[i].rstrip()
            
            # Skip empty lines
            if not line:
                fixed_lines.append('')
                i += 1
                continue
            
            # Check if line ends with hyphen (word break)
            if line.endswith('-') and i + 1 < len(lines):
                next_line = lines[i + 1].lstrip()
                # Join and remove hyphen
                line = line[:-1] + next_line
                i += 2
                fixed_lines.append(line)
                continue
            
            # Check if line ends mid-word (lowercase, no punctuation)
            if (i + 1 < len(lines) and 
                line and 
                line[-1].isalpha() and 
                line[-1].islower() and
                not line.endswith(('.', '!', '?', ':', ';'))):
                next_line = lines[i + 1].lstrip()
                if next_line and next_line[0].islower():
                    # Join with space
                    line = line + ' ' + next_line
                    i += 2
                    fixed_lines.append(line)
                    continue
            
            # Normal line
            fixed_lines.append(line)
            i += 1
        
        return '\n'.join(fixed_lines)
    
    def _normalize_text(self, raw_text: str) -> str:
        """
        Stage 3: Document Normalization
        
        Cleans and normalizes the raw extracted text.
        
        WHY THIS STAGE EXISTS:
        - Remove PDF artifacts (form feeds, extra whitespace)
        - Normalize whitespace for consistent processing
        - Reconstruct paragraphs from broken lines
        - Produce clean, readable text for chunking
        
        IMPORTANT: This is NOT chunking or splitting.
        We're just cleaning the text while keeping it whole.
        
        Args:
            raw_text: Raw text from PDF parser
            
        Returns:
            Clean, normalized text as a single string
        """
        text = raw_text
        
        # Step 1: Remove form feeds and other control characters
        # WHY: These are PDF artifacts, not content
        text = re.sub(r'[\f\r\v]', '', text)
        
        # Step 2: Normalize multiple spaces to single space
        # WHY: PDFs often have irregular spacing
        text = re.sub(r' +', ' ', text)
        
        # Step 3: Normalize multiple newlines to max 2
        # WHY: Preserve paragraph breaks but remove excessive whitespace
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        # Step 4: Remove leading/trailing whitespace from each line
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)
        
        # Step 5: Reconstruct paragraphs
        # WHY: PDFs often break paragraphs into multiple lines
        # We want to join lines within paragraphs but keep paragraph breaks
        paragraphs = text.split('\n\n')
        reconstructed = []
        
        for para in paragraphs:
            # Join lines within paragraph with space
            para_text = ' '.join(para.split('\n'))
            # Normalize multiple spaces again
            para_text = re.sub(r' +', ' ', para_text)
            if para_text.strip():
                reconstructed.append(para_text.strip())
        
        # Join paragraphs with double newline
        clean_text = '\n\n'.join(reconstructed)
        
        # Final cleanup: strip leading/trailing whitespace
        clean_text = clean_text.strip()
        
        return clean_text
    
    def _extract_metadata(
        self, 
        pdf_path: Path, 
        clean_text: str,
        page_count: int
    ) -> Dict:
        """
        Stage 4: Metadata Extraction
        
        Extracts lightweight ingestion-level metadata.
        
        WHY THIS STAGE EXISTS:
        - Provide document-level context for downstream layers
        - Enable filtering and routing based on document properties
        - Support debugging and observability
        
        IMPORTANT: This is LIGHTWEIGHT metadata only.
        The chunking layer will add chunk-level metadata.
        The index layer will add retrieval metadata.
        
        Args:
            pdf_path: Path to original PDF
            clean_text: Normalized text
            page_count: Number of pages in PDF
            
        Returns:
            Dictionary of metadata
        """
        # Generate deterministic document ID
        # WHY: Same document should get same ID across runs
        # HOW: Hash the file path + first 1000 chars (stable but unique)
        content_sample = clean_text[:1000] if len(clean_text) > 1000 else clean_text
        id_string = f"{pdf_path.name}:{content_sample}"
        document_id = hashlib.sha256(id_string.encode()).hexdigest()[:16]
        
        # Extract basic text statistics
        total_characters = len(clean_text)
        words = clean_text.split()
        total_words = len(words)
        
        # Split by double newline to detect paragraphs
        paragraphs = [p for p in clean_text.split('\n\n') if p.strip()]
        total_paragraphs = len(paragraphs)
        avg_paragraph_length = (
            total_words / total_paragraphs if total_paragraphs > 0 else 0
        )
        
        # Detect headings (simple heuristic: short lines in CAPS or Title Case)
        has_headings = self._detect_headings(clean_text)
        
        # Extract dates (simple patterns)
        dates_detected = self._extract_dates(clean_text)
        
        # Extract times (simple patterns)
        times_detected = self._extract_times(clean_text)
        
        # Calculate numeric density
        numeric_density = self._calculate_numeric_density(clean_text)
        
        # Try to extract title (first non-empty line, if short and looks like title)
        title = self._extract_title(clean_text, pdf_path)
        
        # Detect language (simple heuristic)
        language = self._detect_language(clean_text)
        
        # Build metadata dictionary
        metadata = {
            # Identity
            "document_id": document_id,
            "document_type": self.document_type,
            "source_file": str(pdf_path.name),
            "source_path": str(pdf_path.absolute()),
            
            # Content
            "title": title,
            "language": language,
            
            # Statistics
            "page_count": page_count,
            "total_characters": total_characters,
            "total_words": total_words,
            "total_paragraphs": total_paragraphs,
            "avg_paragraph_length": round(avg_paragraph_length, 1),
            
            # Structure
            "has_headings": has_headings,
            
            # Entities (lightweight)
            "dates_detected": dates_detected[:10],  # Limit to first 10
            "times_detected": times_detected[:10],  # Limit to first 10
            
            # Density
            "numeric_density": numeric_density,
            
            # Provenance
            "ingested_at": datetime.utcnow().isoformat() + "Z",
            "ingestion_pipeline_version": "1.0",
        }
        
        return metadata
    
    def _detect_headings(self, text: str) -> bool:
        """
        Detect if document has section headings.
        
        Simple heuristic: Look for short lines (< 60 chars) that are:
        - All caps, OR
        - Title Case, OR
        - Followed by blank line
        """
        lines = text.split('\n')
        heading_count = 0
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line or len(line) > 60:
                continue
            
            # Check if all caps
            if line.isupper() and len(line.split()) <= 8:
                heading_count += 1
            
            # Check if Title Case (most words start with capital)
            words = line.split()
            if len(words) <= 8:
                title_words = sum(1 for w in words if w[0].isupper())
                if title_words >= len(words) * 0.7:
                    heading_count += 1
        
        # If we found several potential headings, return True
        return heading_count >= 3
    
    def _extract_dates(self, text: str) -> List[str]:
        """
        Extract date patterns from text.
        
        Simple patterns: MM/DD/YYYY, DD-MM-YYYY, Month DD, YYYY, etc.
        """
        date_patterns = [
            r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',  # 12/31/2023 or 31-12-2023
            r'\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b',    # 2023-12-31
            r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}\b',  # December 31, 2023
        ]
        
        dates = []
        for pattern in date_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            dates.extend(matches)
        
        # Return unique dates, preserving order
        seen = set()
        unique_dates = []
        for date in dates:
            if date not in seen:
                seen.add(date)
                unique_dates.append(date)
        
        return unique_dates
    
    def _extract_times(self, text: str) -> List[str]:
        """
        Extract time patterns from text.
        
        Simple patterns: HH:MM, HH:MM:SS, HH:MM AM/PM
        """
        time_patterns = [
            r'\b\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM|am|pm)?\b',
        ]
        
        times = []
        for pattern in time_patterns:
            matches = re.findall(pattern, text)
            times.extend(matches)
        
        # Return unique times, preserving order
        seen = set()
        unique_times = []
        for time in times:
            if time not in seen:
                seen.add(time)
                unique_times.append(time)
        
        return unique_times
    
    def _calculate_numeric_density(self, text: str) -> str:
        """
        Calculate density of numbers in text.
        
        Returns: "low", "medium", or "high"
        
        WHY: Helps identify tables, financial docs, forms vs. prose
        """
        # Count numeric characters
        numeric_chars = sum(1 for c in text if c.isdigit())
        total_chars = len(text)
        
        if total_chars == 0:
            return "low"
        
        density = numeric_chars / total_chars
        
        if density < 0.05:
            return "low"
        elif density < 0.15:
            return "medium"
        else:
            return "high"
    
    def _extract_title(self, text: str, pdf_path: Path) -> str:
        """
        Extract document title (best-effort).
        
        Strategy:
        1. Use first non-empty line if it looks like a title
        2. Fall back to filename
        """
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        
        if not lines:
            return pdf_path.stem
        
        first_line = lines[0]
        
        # If first line is short and looks like a title, use it
        if len(first_line) < 100 and not first_line.endswith(('.', ',', ';')):
            return first_line
        
        # Otherwise use filename
        return pdf_path.stem
    
    def _detect_language(self, text: str) -> str:
        """
        Detect document language (simple heuristic).
        
        For production, use langdetect or similar.
        For now, assume English.
        
        WHY: Enables language-specific processing in later layers
        """
        # TODO: Implement proper language detection
        # For now, assume English
        return "en"


# Production-ready factory function
def create_ingestion_pipeline(document_type: str = "pdf_document") -> PDFIngestionPipeline:
    """
    Factory function to create a configured ingestion pipeline.
    
    WHY: Provides clean interface for importing and using this layer.
    
    Args:
        document_type: Type label for documents (used in metadata)
        
    Returns:
        Configured PDFIngestionPipeline instance
    """
    return PDFIngestionPipeline(document_type=document_type)

