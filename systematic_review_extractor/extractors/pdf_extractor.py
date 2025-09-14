"""PDF text extraction utilities."""

import io
import magic
from typing import Optional, List, Tuple
from pathlib import Path
from pypdf import PdfReader
from loguru import logger


class PDFExtractor:
    """Extract text from PDF files."""
    
    def __init__(self):
        """Initialize PDF extractor."""
        self.supported_types = {'application/pdf'}
    
    def is_pdf(self, file_path: Path) -> bool:
        """Check if file is a PDF."""
        try:
            mime_type = magic.from_file(str(file_path), mime=True)
            return mime_type in self.supported_types
        except Exception as e:
            logger.warning(f"Could not determine file type for {file_path}: {e}")
            # Fallback to extension check
            return file_path.suffix.lower() == '.pdf'
    
    def extract_text(self, file_path: Path) -> Tuple[str, List[str]]:
        """
        Extract text from PDF file.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Tuple of (full_text, pages_text_list)
            
        Raises:
            ValueError: If file is not a PDF or cannot be read
        """
        if not file_path.exists():
            raise ValueError(f"File does not exist: {file_path}")
            
        if not self.is_pdf(file_path):
            raise ValueError(f"File is not a PDF: {file_path}")
        
        try:
            with open(file_path, 'rb') as file:
                reader = PdfReader(file)
                pages_text = []
                
                for page_num, page in enumerate(reader.pages, 1):
                    try:
                        text = page.extract_text()
                        pages_text.append(text)
                        logger.debug(f"Extracted text from page {page_num}")
                    except Exception as e:
                        logger.warning(f"Could not extract text from page {page_num}: {e}")
                        pages_text.append("")
                
                full_text = "\n\n".join(pages_text)
                logger.info(f"Successfully extracted text from {len(pages_text)} pages")
                
                return full_text, pages_text
                
        except Exception as e:
            logger.error(f"Failed to extract text from {file_path}: {e}")
            raise ValueError(f"Could not read PDF file: {e}")
    
    def extract_metadata(self, file_path: Path) -> dict:
        """
        Extract metadata from PDF file.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Dictionary containing PDF metadata
        """
        if not file_path.exists():
            raise ValueError(f"File does not exist: {file_path}")
            
        try:
            with open(file_path, 'rb') as file:
                reader = PdfReader(file)
                metadata = {}
                
                if reader.metadata:
                    metadata.update({
                        'title': reader.metadata.get('/Title', ''),
                        'author': reader.metadata.get('/Author', ''),
                        'subject': reader.metadata.get('/Subject', ''),
                        'creator': reader.metadata.get('/Creator', ''),
                        'producer': reader.metadata.get('/Producer', ''),
                        'creation_date': reader.metadata.get('/CreationDate', ''),
                        'modification_date': reader.metadata.get('/ModDate', ''),
                    })
                
                metadata['page_count'] = len(reader.pages)
                metadata['is_encrypted'] = reader.is_encrypted
                
                return metadata
                
        except Exception as e:
            logger.error(f"Failed to extract metadata from {file_path}: {e}")
            return {}


class TextProcessor:
    """Process and clean extracted text."""
    
    def __init__(self):
        """Initialize text processor."""
        pass
    
    def clean_text(self, text: str) -> str:
        """
        Clean and normalize extracted text.
        
        Args:
            text: Raw extracted text
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Remove excessive whitespace
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Strip whitespace and normalize spaces
            cleaned_line = ' '.join(line.strip().split())
            if cleaned_line:  # Only add non-empty lines
                cleaned_lines.append(cleaned_line)
        
        # Rejoin lines with single newlines
        cleaned_text = '\n'.join(cleaned_lines)
        
        # Remove excessive newlines (more than 2 consecutive)
        import re
        cleaned_text = re.sub(r'\n{3,}', '\n\n', cleaned_text)
        
        return cleaned_text.strip()
    
    def split_into_sections(self, text: str) -> dict:
        """
        Split text into common research paper sections.
        
        Args:
            text: Full paper text
            
        Returns:
            Dictionary with section names as keys and text as values
        """
        import re
        
        sections = {
            'title': '',
            'abstract': '',
            'introduction': '',
            'methods': '',
            'results': '',
            'discussion': '',
            'conclusion': '',
            'references': '',
            'other': ''
        }
        
        # Common section headers (case insensitive)
        section_patterns = {
            'abstract': r'\b(abstract|summary)\b',
            'introduction': r'\b(introduction|background)\b',
            'methods': r'\b(methods?|methodology|materials?\s+and\s+methods?)\b',
            'results': r'\b(results?|findings?)\b',
            'discussion': r'\b(discussion|analysis)\b',
            'conclusion': r'\b(conclusion|conclusions?|summary)\b',
            'references': r'\b(references?|bibliography|literature\s+cited)\b',
        }
        
        # Try to identify sections
        lines = text.split('\n')
        current_section = 'other'
        section_content = {key: [] for key in sections.keys()}
        
        for line in lines:
            line_lower = line.lower().strip()
            
            # Check if line is a section header
            found_section = None
            for section_name, pattern in section_patterns.items():
                if re.search(pattern, line_lower, re.IGNORECASE):
                    # Check if this looks like a header (short line, possibly with numbers)
                    if len(line.strip()) < 100 and not line.strip().endswith('.'):
                        found_section = section_name
                        break
            
            if found_section:
                current_section = found_section
            else:
                section_content[current_section].append(line)
        
        # Convert lists back to strings
        for section_name in sections:
            sections[section_name] = '\n'.join(section_content[section_name]).strip()
        
        return sections