"""
Text normalization and post-processing pipeline for contract documents.
"""

import re
import logging
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum
import unicodedata
import spacy
from spacy.lang.pt import Portuguese
from spacy.lang.en import English

from app.models.schemas import PageContent, TextBlock

logger = logging.getLogger(__name__)


class TextProcessingError(Exception):
    """Exception raised during text processing."""
    pass


@dataclass
class NormalizationResult:
    """Result of text normalization process."""
    original_text: str
    normalized_text: str
    changes_made: List[str]
    legal_terms_found: List[str]
    structure_preserved: bool


class ContractAbbreviations:
    """Dictionary of common contract abbreviations and their expansions."""
    
    ABBREVIATIONS = {
        # Portuguese contract terms (prioritized)
        "art.": "artigo",
        "arts.": "artigos", 
        "inc.": "inciso",
        "incs.": "incisos",
        "par.": "parágrafo",
        "pars.": "parágrafos",
        "§": "parágrafo",
        "cláus.": "cláusula",
        "cl.": "cláusula",
        "cls.": "cláusulas",
        "contrat.": "contratante",
        "contratd.": "contratado",
        "resp.": "responsável",
        "obrig.": "obrigação",
        "obrigações": "obrigações",
        "pag.": "pagamento",
        "venc.": "vencimento",
        "val.": "valor",
        "qtd.": "quantidade",
        "desc.": "desconto",
        "juros": "juros",
        "multa": "multa",
        "rescis.": "rescisão",
        "renov.": "renovação",
        "prorrog.": "prorrogação",
        "vig.": "vigência",
        "exec.": "execução",
        "cumpr.": "cumprimento",
        "inadimpl.": "inadimplemento",
        "foro": "foro",
        "comarca": "comarca",
        "juízo": "juízo",
        "test.": "testemunha",
        "tests.": "testemunhas",
        "ass.": "assinatura",
        "doc.": "documento",
        "docs.": "documentos",
        "certid.": "certidão",
        "proc.": "processo",
        "n°": "número",
        "nº": "número",
        "cpf": "CPF",
        "cnpj": "CNPJ",
        "rg": "RG",
        "cep": "CEP",
        
        # English contract terms
        "agmt.": "agreement",
        "agrmt.": "agreement",
        "cont.": "contract",
        "contr.": "contract",
        "sect.": "section",
        "subsect.": "subsection",
        "para.": "paragraph",
        "subpara.": "subparagraph",
        "cl.": "clause",
        "subcl.": "subclause",
        "art.": "article",
        "sched.": "schedule",
        "app.": "appendix",
        "exh.": "exhibit",
        "attach.": "attachment",
        "incl.": "including",
        "excl.": "excluding",
        "ltd.": "limited",
        "corp.": "corporation",
        "inc.": "incorporated",
        "llc": "limited liability company",
        "co.": "company",
        "assoc.": "association",
        "dept.": "department",
        "div.": "division",
        "mgmt.": "management",
        "admin.": "administration",
        "exec.": "executive",
        "dir.": "director",
        "mgr.": "manager",
        "repr.": "representative",
        "auth.": "authorized",
        "sig.": "signature",
        "eff.": "effective",
        "term.": "termination",
        "renew.": "renewal",
        "ext.": "extension",
        "amend.": "amendment",
        "mod.": "modification",
        "supp.": "supplement",
        "add.": "addendum",
        "rev.": "revision",
        "ver.": "version",
        "ref.": "reference",
        "spec.": "specification",
        "req.": "requirement",
        "std.": "standard",
        "proc.": "procedure",
        "meth.": "method",
        "tech.": "technical",
        "comm.": "commercial",
        "fin.": "financial",
        "acct.": "account",
        "inv.": "invoice",
        "pmt.": "payment",
        "amt.": "amount",
        "qty.": "quantity",
        "desc.": "description",
        "addr.": "address",
        "tel.": "telephone",
        "fax": "facsimile",
        "email": "electronic mail",
        "www.": "world wide web",
        "etc.": "et cetera",
        "i.e.": "that is",
        "e.g.": "for example",
        "vs.": "versus",
        "v.": "versus",
        "approx.": "approximately",
        "est.": "estimated",
        "max.": "maximum",
        "min.": "minimum",
        "avg.": "average",
        "std.": "standard",
        "temp.": "temporary",
        "perm.": "permanent",
        "immed.": "immediate",
        "asap": "as soon as possible",
        "tbd": "to be determined",
        "tba": "to be announced",
        "n/a": "not applicable",
        "w/": "with",
        "w/o": "without",
        "re:": "regarding",
        "attn:": "attention",
        "cc:": "carbon copy",
        "bcc:": "blind carbon copy",
        "fwd:": "forward",
        "subj:": "subject"
    }
    
    @classmethod
    def expand_abbreviations(cls, text: str) -> Tuple[str, List[str]]:
        """Expand abbreviations in text and return expanded text with list of changes."""
        expanded_text = text
        changes = []
        
        # Detect language to prioritize correct abbreviations
        # Simple heuristic based on common words
        portuguese_indicators = ["de", "da", "do", "das", "dos", "em", "na", "no", "nas", "nos", 
                               "para", "por", "com", "sem", "sobre", "entre", "até", "desde",
                               "que", "não", "são", "estabelece", "cláusula"]
        
        english_indicators = ["the", "and", "or", "of", "in", "on", "at", "to", "for", "with",
                            "by", "from", "about", "into", "through", "during", "before", "after",
                            "that", "not", "are", "establishes", "clause"]
        
        words = text.lower().split()
        pt_count = sum(1 for word in words if word in portuguese_indicators)
        en_count = sum(1 for word in words if word in english_indicators)
        
        is_portuguese = pt_count >= en_count
        
        # Create language-specific abbreviation list
        pt_abbrevs = {
            "art.": "artigo", "arts.": "artigos", "inc.": "inciso", "incs.": "incisos",
            "par.": "parágrafo", "pars.": "parágrafos", "§": "parágrafo",
            "cláus.": "cláusula", "cl.": "cláusula", "cls.": "cláusulas",
            "contrat.": "contratante", "contratd.": "contratado",
            "resp.": "responsável", "obrig.": "obrigação",
            "pag.": "pagamento", "venc.": "vencimento", "val.": "valor",
            "qtd.": "quantidade", "desc.": "desconto",
            "rescis.": "rescisão", "renov.": "renovação", "prorrog.": "prorrogação",
            "vig.": "vigência", "exec.": "execução", "cumpr.": "cumprimento",
            "inadimpl.": "inadimplemento", "test.": "testemunha", "tests.": "testemunhas",
            "ass.": "assinatura", "doc.": "documento", "docs.": "documentos",
            "certid.": "certidão", "proc.": "processo",
            "n°": "número", "nº": "número"
        }
        
        en_abbrevs = {
            "agmt.": "agreement", "agrmt.": "agreement",
            "cont.": "contract", "contr.": "contract",
            "sect.": "section", "subsect.": "subsection",
            "para.": "paragraph", "subpara.": "subparagraph",
            "cl.": "clause", "subcl.": "subclause",
            "sched.": "schedule", "app.": "appendix", "exh.": "exhibit",
            "attach.": "attachment", "incl.": "including", "excl.": "excluding",
            "ltd.": "limited", "corp.": "corporation", "llc": "limited liability company",
            "co.": "company", "assoc.": "association",
            "dept.": "department", "div.": "division",
            "mgmt.": "management", "admin.": "administration",
            "dir.": "director", "mgr.": "manager",
            "repr.": "representative", "auth.": "authorized",
            "sig.": "signature", "eff.": "effective",
            "term.": "termination", "renew.": "renewal", "ext.": "extension",
            "amend.": "amendment", "mod.": "modification",
            "supp.": "supplement", "add.": "addendum",
            "rev.": "revision", "ver.": "version",
            "ref.": "reference", "spec.": "specification",
            "req.": "requirement", "std.": "standard",
            "meth.": "method", "tech.": "technical",
            "comm.": "commercial", "fin.": "financial",
            "acct.": "account", "inv.": "invoice",
            "pmt.": "payment", "amt.": "amount",
            "qty.": "quantity", "addr.": "address",
            "tel.": "telephone", "approx.": "approximately",
            "est.": "estimated", "max.": "maximum", "min.": "minimum",
            "avg.": "average", "temp.": "temporary",
            "perm.": "permanent", "immed.": "immediate",
            "asap": "as soon as possible", "tbd": "to be determined",
            "tba": "to be announced", "n/a": "not applicable",
            "w/": "with", "w/o": "without",
            "re:": "regarding", "attn:": "attention",
            "cc:": "carbon copy", "bcc:": "blind carbon copy",
            "fwd:": "forward", "subj:": "subject"
        }
        
        # Select appropriate abbreviations based on language
        abbrevs_to_use = pt_abbrevs if is_portuguese else en_abbrevs
        
        # Sort by length (longest first) to avoid partial replacements
        sorted_abbrevs = sorted(abbrevs_to_use.items(), key=lambda x: len(x[0]), reverse=True)
        
        for abbrev, expansion in sorted_abbrevs:
            # Create pattern that matches the abbreviation with word boundaries
            # Handle special characters in abbreviations
            escaped_abbrev = re.escape(abbrev)
            # Use word boundaries but be more flexible with punctuation
            pattern = r'(?<!\w)' + escaped_abbrev + r'(?!\w)'
            
            # Case-insensitive replacement
            matches = list(re.finditer(pattern, expanded_text, re.IGNORECASE))
            if matches:
                # Replace from right to left to maintain positions
                for match in reversed(matches):
                    start, end = match.span()
                    expanded_text = expanded_text[:start] + expansion + expanded_text[end:]
                changes.append(f"'{abbrev}' → '{expansion}'")
        
        return expanded_text, changes


class LegalTermProcessor:
    """Processor for legal terms validation and correction using spaCy."""
    
    def __init__(self):
        self.nlp_pt = None
        self.nlp_en = None
        self._load_models()
        
        # Common legal terms that should be preserved/validated
        self.legal_terms_pt = {
            "contrato", "contratante", "contratado", "cláusula", "parágrafo",
            "artigo", "inciso", "obrigação", "direito", "dever", "responsabilidade",
            "pagamento", "vencimento", "prazo", "multa", "juros", "correção",
            "rescisão", "resolução", "resilição", "renovação", "prorrogação",
            "vigência", "eficácia", "validade", "nulidade", "anulabilidade",
            "inadimplemento", "mora", "culpa", "dolo", "caso fortuito",
            "força maior", "foro", "comarca", "juízo", "arbitragem",
            "mediação", "conciliação", "testemunha", "fiador", "avalista",
            "garantia", "caução", "penhor", "hipoteca", "alienação",
            "cessão", "subcontratação", "terceirização", "consórcio",
            "joint venture", "sociedade", "empresa", "pessoa física",
            "pessoa jurídica", "capacidade", "representação", "mandato",
            "procuração", "outorga", "anuência", "consentimento", "acordo",
            "ajuste", "pacto", "convenção", "protocolo", "termo",
            "instrumento", "documento", "certidão", "atestado", "declaração"
        }
        
        self.legal_terms_en = {
            "contract", "agreement", "party", "parties", "contractor", "contractee",
            "clause", "section", "paragraph", "article", "subsection", "provision",
            "obligation", "duty", "right", "responsibility", "liability",
            "payment", "consideration", "compensation", "remuneration", "fee",
            "penalty", "damages", "interest", "default", "breach", "violation",
            "termination", "expiration", "renewal", "extension", "amendment",
            "modification", "supplement", "addendum", "schedule", "exhibit",
            "attachment", "appendix", "validity", "enforceability", "legality",
            "compliance", "performance", "execution", "fulfillment", "delivery",
            "acceptance", "approval", "consent", "authorization", "permission",
            "waiver", "release", "discharge", "indemnity", "indemnification",
            "guarantee", "warranty", "representation", "covenant", "undertaking",
            "assignment", "delegation", "novation", "substitution", "replacement",
            "arbitration", "mediation", "litigation", "dispute", "resolution",
            "jurisdiction", "venue", "governing law", "applicable law",
            "force majeure", "act of god", "impossibility", "frustration",
            "commercial impracticability", "hardship", "change of circumstances",
            "confidentiality", "non-disclosure", "proprietary", "intellectual property",
            "copyright", "trademark", "patent", "trade secret", "know-how",
            "severability", "entire agreement", "integration", "merger",
            "parol evidence", "statute of frauds", "statute of limitations",
            "good faith", "fair dealing", "reasonable", "material", "substantial"
        }
    
    def _load_models(self):
        """Load spaCy models for Portuguese and English."""
        try:
            # Try to load Portuguese model
            self.nlp_pt = spacy.load("pt_core_news_sm")
        except OSError:
            logger.warning("Portuguese spaCy model not found, using basic Portuguese model")
            try:
                self.nlp_pt = Portuguese()
            except Exception as e:
                logger.error(f"Failed to load Portuguese model: {e}")
                self.nlp_pt = None
        
        try:
            # Try to load English model
            self.nlp_en = spacy.load("en_core_web_sm")
        except OSError:
            logger.warning("English spaCy model not found, using basic English model")
            try:
                self.nlp_en = English()
            except Exception as e:
                logger.error(f"Failed to load English model: {e}")
                self.nlp_en = None
    
    def detect_language(self, text: str) -> str:
        """Detect the primary language of the text."""
        # Simple heuristic based on common words
        portuguese_indicators = ["de", "da", "do", "das", "dos", "em", "na", "no", "nas", "nos", 
                               "para", "por", "com", "sem", "sobre", "entre", "até", "desde",
                               "contrato", "cláusula", "parágrafo", "artigo", "que", "não", "são"]
        
        english_indicators = ["the", "and", "or", "of", "in", "on", "at", "to", "for", "with",
                            "by", "from", "about", "into", "through", "during", "before", "after",
                            "contract", "agreement", "clause", "section", "that", "not", "are"]
        
        words = text.lower().split()
        pt_count = sum(1 for word in words if word in portuguese_indicators)
        en_count = sum(1 for word in words if word in english_indicators)
        
        return "pt" if pt_count > en_count else "en"
    
    def validate_legal_terms(self, text: str) -> Tuple[str, List[str]]:
        """Validate and correct legal terms in text."""
        language = self.detect_language(text)
        legal_terms = self.legal_terms_pt if language == "pt" else self.legal_terms_en
        nlp = self.nlp_pt if language == "pt" else self.nlp_en
        
        found_terms = []
        corrected_text = text
        
        # Always use simple term detection as primary method
        # This ensures we find terms even without spaCy models
        text_lower = text.lower()
        for term in legal_terms:
            # Use word boundaries to find complete terms
            pattern = r'\b' + re.escape(term.lower()) + r'\b'
            if re.search(pattern, text_lower):
                found_terms.append(term)
        
        # If spaCy is available, try to enhance the results
        if nlp is not None:
            try:
                doc = nlp(text)
                
                # Extract additional legal terms found through spaCy
                for token in doc:
                    if hasattr(token, 'lemma_') and token.lemma_.lower() in legal_terms:
                        if token.lemma_.lower() not in found_terms:
                            found_terms.append(token.lemma_.lower())
                
                # Extract named entities that might be legal terms
                if hasattr(doc, 'ents'):
                    for ent in doc.ents:
                        if (hasattr(ent, 'label_') and 
                            ent.label_ in ["ORG", "PERSON", "LAW", "LEGAL"] and 
                            ent.text.lower() in legal_terms and
                            ent.text.lower() not in found_terms):
                            found_terms.append(ent.text.lower())
                
            except Exception as e:
                logger.warning(f"Error in spaCy processing: {e}")
        
        # Remove duplicates while preserving order
        found_terms = list(dict.fromkeys(found_terms))
        
        return corrected_text, found_terms


class TextNormalizer:
    """Main text normalization and post-processing pipeline."""
    
    def __init__(self):
        self.legal_processor = LegalTermProcessor()
        self.abbreviations = ContractAbbreviations()
    
    def clean_text(self, text: str) -> Tuple[str, List[str]]:
        """Remove special characters and fix encoding issues."""
        if not text:
            return "", []
        
        changes = []
        original_text = text
        
        # Normalize Unicode characters (use NFC instead of NFKC to avoid breaking words)
        normalized_unicode = unicodedata.normalize('NFC', text)
        if normalized_unicode != text:
            text = normalized_unicode
            changes.append("Unicode normalization applied")
        
        # Fix common encoding issues
        encoding_fixes = {
            'â€™': "'",  # Smart apostrophe
            'â€œ': '"',  # Smart quote left
            'â€': '"',   # Smart quote right
            'â€"': '—',  # Em dash
            'â€"': '–',  # En dash
            'Ã¡': 'á',   # á with encoding issue
            'Ã©': 'é',   # é with encoding issue
            'Ã­': 'í',   # í with encoding issue
            'Ã³': 'ó',   # ó with encoding issue
            'Ãº': 'ú',   # ú with encoding issue
            'Ã ': 'à',   # à with encoding issue
            'Ã§': 'ç',   # ç with encoding issue
            'Ã±': 'ñ',   # ñ with encoding issue
        }
        
        for bad_encoding, correct_char in encoding_fixes.items():
            if bad_encoding in text:
                text = text.replace(bad_encoding, correct_char)
                changes.append(f"Fixed encoding: '{bad_encoding}' → '{correct_char}'")
        
        # Remove or replace problematic special characters
        # Keep important punctuation and legal symbols
        important_chars = set('.,;:!?()[]{}"\'-–—§°ªº%$€£¥₹¢₽₩₪₨₦₡₵₸₴₲₱₭₫₯₰₳₴₵₶₷₸₹₺₻₼₽₾₿')
        
        # Remove control characters but keep newlines and tabs
        # Be more conservative to avoid breaking words
        cleaned_chars = []
        for char in text:
            if char.isprintable() or char in '\n\t\r':
                cleaned_chars.append(char)
            elif char in important_chars:
                cleaned_chars.append(char)
            elif ord(char) < 32:  # Only replace actual control characters
                cleaned_chars.append(' ')
            else:
                # Keep other characters to avoid breaking words
                cleaned_chars.append(char)
        
        cleaned_text = ''.join(cleaned_chars)
        if cleaned_text != text:
            changes.append("Removed/replaced control characters")
        
        return cleaned_text, changes
    
    def normalize_spacing(self, text: str) -> Tuple[str, List[str]]:
        """Normalize spacing (multiple spaces to single space)."""
        if not text:
            return "", []
        
        changes = []
        original_text = text
        
        # Replace multiple spaces with single space
        text = re.sub(r' +', ' ', text)
        if text != original_text:
            changes.append("Normalized multiple spaces to single space")
        
        # Replace multiple tabs with single space
        text = re.sub(r'\t+', ' ', text)
        if text != original_text:
            changes.append("Replaced tabs with spaces")
        
        # Normalize spaces around punctuation
        # Add space after punctuation if missing
        text = re.sub(r'([.!?;:,])([A-Za-z])', r'\1 \2', text)
        
        # Remove space before punctuation
        text = re.sub(r' +([.!?;:,])', r'\1', text)
        
        # Normalize spaces around parentheses and brackets
        text = re.sub(r' +([)\]}])', r'\1', text)  # Remove space before closing
        text = re.sub(r'([(\[{]) +', r'\1', text)  # Remove space after opening
        
        if text != original_text:
            changes.append("Normalized spacing around punctuation")
        
        return text, changes
    
    def standardize_line_breaks(self, text: str) -> Tuple[str, List[str]]:
        """Standardize line breaks for paragraph formatting."""
        if not text:
            return "", []
        
        changes = []
        original_text = text
        
        # Normalize different line ending types
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # Remove trailing spaces from lines
        lines = text.split('\n')
        lines = [line.rstrip() for line in lines]
        text = '\n'.join(lines)
        
        # Standardize paragraph breaks
        # Multiple consecutive newlines become double newline (paragraph break)
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        # Single newlines within paragraphs become spaces (unless they're intentional breaks)
        # This is tricky - we need to preserve intentional line breaks
        # Heuristic: if line ends with punctuation, it's likely end of sentence
        lines = text.split('\n')
        processed_lines = []
        
        i = 0
        while i < len(lines):
            current_line = lines[i].strip()
            
            if not current_line:
                # Empty line - preserve as paragraph break
                processed_lines.append('')
                i += 1
                continue
            
            # Check if this line should be joined with the next
            if (i + 1 < len(lines) and 
                lines[i + 1].strip() and  # Next line is not empty
                not current_line.endswith(('.', '!', '?', ':', ';')) and  # Current doesn't end with punctuation
                not lines[i + 1].strip()[0].isupper()):  # Next doesn't start with capital
                
                # Join with next line
                processed_lines.append(current_line + ' ' + lines[i + 1].strip())
                i += 2
            else:
                processed_lines.append(current_line)
                i += 1
        
        standardized_text = '\n'.join(processed_lines)
        
        if standardized_text != original_text:
            changes.append("Standardized line breaks and paragraph formatting")
        
        return standardized_text, changes
    
    def preserve_numbered_clauses(self, text: str) -> Tuple[str, List[str]]:
        """Preserve structure of numbered clauses and sections."""
        if not text:
            return "", []
        
        changes = []
        original_text = text
        
        # Patterns for numbered clauses (Portuguese and English)
        # Be more specific to avoid matching regular words
        clause_patterns = [
            r'(\n|^)(\d+\.?\d*\.?\s*[-–—]?\s*)',  # 1. or 1.1. or 1 -
            r'(\n|^)([IVX]+\.?\s*[-–—]?\s*)',     # Roman numerals I. II. III.
            r'(\n|^)([a-z]\)\s*[-–—]?\s*)',       # a) b) c) - must have parenthesis
            r'(\n|^)([A-Z]\)\s*[-–—]?\s*)',       # A) B) C) - must have parenthesis
            r'(\n|^)(§\s*\d+\.?\d*\.?\s*)',       # § 1. § 1.1.
            r'(\n|^)(Art\.?\s*\d+\.?\d*\.?\s*)',  # Art. 1. Artigo 1.
            r'(\n|^)(Cláusula\s+\d+\.?\d*\.?\s*)', # Cláusula 1.
            r'(\n|^)(Parágrafo\s+\d+\.?\d*\.?\s*)', # Parágrafo 1.
            r'(\n|^)(Inciso\s+[IVX]+\.?\s*)',     # Inciso I.
        ]
        
        # Ensure proper spacing and formatting around numbered clauses
        for pattern in clause_patterns:
            # Find all matches
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            if matches:
                changes.append(f"Preserved numbered clause structure: {pattern}")
                
                # Ensure there's a newline before each clause (except the first)
                for match in reversed(matches):  # Process in reverse to maintain positions
                    start, end = match.span()
                    clause_marker = match.group(2)
                    
                    # Ensure proper spacing after clause marker
                    if not clause_marker.endswith(' '):
                        text = text[:match.start(2)] + clause_marker + ' ' + text[match.end(2):]
        
        # Ensure proper indentation for sub-clauses
        lines = text.split('\n')
        processed_lines = []
        
        for line in lines:
            stripped = line.strip()
            if stripped:
                # Check if it's a sub-clause (like 1.1, a), etc.)
                # Be more specific to avoid matching regular words
                if (re.match(r'^\d+\.\d+\.?\s', stripped) or 
                    re.match(r'^[a-z]\)\s', stripped) or
                    re.match(r'^[a-z]\.\s', stripped)):
                    # Add slight indentation for sub-clauses
                    processed_lines.append('    ' + stripped)
                elif (re.match(r'^\d+\.?\s', stripped) or 
                      re.match(r'^[IVX]+\.?\s', stripped)):
                    # Main clauses - no extra indentation
                    processed_lines.append(stripped)
                else:
                    # Regular text - preserve original indentation logic
                    processed_lines.append(stripped)
            else:
                processed_lines.append('')
        
        structured_text = '\n'.join(processed_lines)
        
        if structured_text != original_text:
            changes.append("Applied structured formatting to numbered clauses")
        
        return structured_text, changes
    
    def normalize_text(self, text: str) -> NormalizationResult:
        """Apply complete text normalization pipeline."""
        if not text:
            return NormalizationResult(
                original_text="",
                normalized_text="",
                changes_made=[],
                legal_terms_found=[],
                structure_preserved=True
            )
        
        original_text = text
        all_changes = []
        
        try:
            # Step 1: Clean text and fix encoding
            text, changes = self.clean_text(text)
            all_changes.extend(changes)
            
            # Step 2: Expand abbreviations (before spacing normalization to avoid issues)
            text, changes = self.abbreviations.expand_abbreviations(text)
            all_changes.extend(changes)
            
            # Step 3: Normalize spacing
            text, changes = self.normalize_spacing(text)
            all_changes.extend(changes)
            
            # Step 4: Standardize line breaks
            text, changes = self.standardize_line_breaks(text)
            all_changes.extend(changes)
            
            # Step 5: Preserve numbered clause structure
            text, changes = self.preserve_numbered_clauses(text)
            all_changes.extend(changes)
            
            # Step 6: Validate and extract legal terms
            text, legal_terms = self.legal_processor.validate_legal_terms(text)
            
            # Final cleanup - remove extra whitespace
            text = text.strip()
            
            # Check if structure was preserved (heuristic)
            structure_preserved = self._check_structure_preservation(original_text, text)
            
            return NormalizationResult(
                original_text=original_text,
                normalized_text=text,
                changes_made=all_changes,
                legal_terms_found=legal_terms,
                structure_preserved=structure_preserved
            )
            
        except Exception as e:
            logger.error(f"Error in text normalization: {e}")
            raise TextProcessingError(f"Failed to normalize text: {str(e)}")
    
    def _check_structure_preservation(self, original: str, normalized: str) -> bool:
        """Check if the original structure was preserved during normalization."""
        # Simple heuristics to check structure preservation
        
        # Check if numbered clauses are still present
        clause_patterns = [r'\d+\.', r'[IVX]+\.', r'[a-z]\)', r'[A-Z]\)', r'§\s*\d+', r'Art\.?\s*\d+']
        
        original_clauses = 0
        normalized_clauses = 0
        
        for pattern in clause_patterns:
            original_clauses += len(re.findall(pattern, original))
            normalized_clauses += len(re.findall(pattern, normalized))
        
        # Structure is preserved if we didn't lose significant clause markers
        # Allow for some variation due to normalization
        if original_clauses > 0:
            preservation_ratio = normalized_clauses / original_clauses
            return preservation_ratio >= 0.8  # Allow 20% loss due to normalization
        
        # If no clauses detected, check paragraph structure
        original_paragraphs = len([p for p in original.split('\n\n') if p.strip()])
        normalized_paragraphs = len([p for p in normalized.split('\n\n') if p.strip()])
        
        if original_paragraphs > 0:
            preservation_ratio = normalized_paragraphs / original_paragraphs
            return preservation_ratio >= 0.7  # Allow 30% variation in paragraph detection
        
        return True  # If no structure detected, assume it's preserved
    
    def process_page_content(self, page_content: PageContent) -> PageContent:
        """Process a PageContent object, normalizing all text while preserving structure."""
        try:
            # Normalize the raw text
            raw_result = self.normalize_text(page_content.raw_text)
            
            # Process individual text blocks
            processed_blocks = []
            for block in page_content.text_blocks:
                block_result = self.normalize_text(block.text)
                
                # Create new text block with normalized text
                processed_block = TextBlock(
                    text=block_result.normalized_text,
                    confidence=block.confidence,
                    bounding_box=block.bounding_box,
                    font_size=block.font_size,
                    is_title=block.is_title
                )
                processed_blocks.append(processed_block)
            
            # Create new PageContent with normalized text
            return PageContent(
                page_number=page_content.page_number,
                text_blocks=processed_blocks,
                raw_text=page_content.raw_text,  # Keep original raw text
                normalized_text=raw_result.normalized_text,
                tables=page_content.tables,
                images=page_content.images
            )
            
        except Exception as e:
            logger.error(f"Error processing page content: {e}")
            # Return original content if processing fails
            return page_content


class TextPostProcessor:
    """High-level text post-processing service."""
    
    def __init__(self):
        self.normalizer = TextNormalizer()
    
    def process_document_pages(self, pages: List[PageContent]) -> List[PageContent]:
        """Process all pages of a document."""
        processed_pages = []
        
        for page in pages:
            try:
                processed_page = self.normalizer.process_page_content(page)
                processed_pages.append(processed_page)
            except Exception as e:
                logger.error(f"Error processing page {page.page_number}: {e}")
                # Keep original page if processing fails
                processed_pages.append(page)
        
        return processed_pages
    
    def get_document_legal_terms(self, pages: List[PageContent]) -> List[str]:
        """Extract all legal terms found in the document."""
        all_terms = set()
        
        for page in pages:
            try:
                result = self.normalizer.normalize_text(page.normalized_text)
                all_terms.update(result.legal_terms_found)
            except Exception as e:
                logger.warning(f"Error extracting legal terms from page {page.page_number}: {e}")
        
        return sorted(list(all_terms))
    
    def get_normalization_summary(self, pages: List[PageContent]) -> Dict[str, any]:
        """Get a summary of normalization changes made across all pages."""
        total_changes = []
        total_legal_terms = set()
        pages_processed = 0
        structure_preserved_count = 0
        
        for page in pages:
            try:
                result = self.normalizer.normalize_text(page.raw_text)
                total_changes.extend(result.changes_made)
                total_legal_terms.update(result.legal_terms_found)
                pages_processed += 1
                if result.structure_preserved:
                    structure_preserved_count += 1
            except Exception as e:
                logger.warning(f"Error getting normalization summary for page {page.page_number}: {e}")
        
        return {
            "pages_processed": pages_processed,
            "total_changes": len(total_changes),
            "unique_change_types": len(set(total_changes)),
            "legal_terms_found": len(total_legal_terms),
            "structure_preservation_rate": structure_preserved_count / max(1, pages_processed),
            "change_details": total_changes[:10],  # First 10 changes for summary
            "legal_terms": sorted(list(total_legal_terms))[:20]  # First 20 terms for summary
        }