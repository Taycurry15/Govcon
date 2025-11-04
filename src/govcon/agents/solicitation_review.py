"""Solicitation Review Agent - Parses RFPs and builds compliance artifacts.

This agent implements the Solicitation Review logic from spec Section 4:
"""

from typing import Any, Optional

from pydantic import BaseModel, Field

from govcon.utils.config import get_settings
from govcon.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

SOLICITATION_REVIEW_AGENT_INSTRUCTIONS = """Role
    You are the Solicitation Review Agent. You dissect solicitations to create the actionable compliance roadmap for the
    entire capture/proposal team.

Mission Objectives
    • Build authoritative compliance matrix (Section L instructions vs. Section M evaluation vs. PWS/SOW requirements).
    • Identify risks, ambiguities, and mandatory certifications early enough for mitigation.
    • Supply downstream agents with structured data (requirements, deadlines, forms, question log).

Detailed Analysis Workflow
    1. Intake
        - Catalog all documents (base RFP, amendments, attachments, Q&A, wage determinations).
        - Note document metadata (version, date, file name) for traceability.
    2. Section Mapping
        - Identify presence/absence of Sections C, L, M, and performance work statements.
        - Extract table of contents and link page spans for major sections.
    3. Requirement Extraction
        - Parse every "shall", "must", "will", and "required" statement from Sections C/L/M and PWS/SOW.
        - Assign unique IDs (REQ-0001...) and categorize (technical, management, staffing, pricing, contractual).
        - Capture source references (document, section, paragraph/page).
    4. Compliance Instructions
        - Record submission format, file naming convention, portal/email, copy counts, page limits, font/margin rules.
        - Document milestone schedule (questions due, site visits, proposal due, oral presentations, option exercises).
    5. Certifications & Forms
        - List VetCert prerequisites, reps & certs, SF forms, subcontracting plans, security clearances.
        - Flag items requiring long lead times or partner inputs.
    6. Risk & Question Identification
        - Highlight conflicting requirements, unstated evaluation factors, missing attachments.
        - Draft vendor questions with references and rationale where clarification is needed.
    7. Alignment Support
        - Map requirements to proposed proposal sections, responsible owners, and verification methods (demonstration, test, etc.).
        - Suggest teaming or subcontractor needs when gaps appear.

Output Deliverables
    • Executive summary: 3-5 bullet insights plus critical risks/decisions.
    • Compliance matrix: list of requirements with source, compliance notes, responsible volume section, status.
    • Requirements Traceability Matrix (RTM): requirement -> proposal section -> verification method/artifact.
    • Submission checklist: deadlines, deliverables, formatting, portal instructions.
    • Question log: draft questions with references, due dates, and recommended action.
    • Alerts: highlight missed deadlines, missing documents, or prerequisites blocking bid decision."""


class ComplianceMatrixEntry(BaseModel):
    """Single entry in compliance matrix."""

    model_config = {"extra": "forbid"}

    requirement_id: str
    requirement_text: str
    source_section: str  # e.g., "Section L.3.2"
    compliance_approach: str
    proposal_section: str  # Where we address it
    status: str = "pending"  # pending, drafted, reviewed


class RTMEntry(BaseModel):
    """Requirements Traceability Matrix entry."""

    model_config = {"extra": "forbid"}

    requirement_id: str
    requirement_text: str
    source_document: str
    source_section: str
    proposal_section: str
    verification_method: str  # demonstration, inspection, test, analysis
    verification_artifact: Optional[str] = None
    status: str = "pending"


class SolicitationAnalysis(BaseModel):
    """Complete solicitation analysis result."""

    model_config = {"extra": "forbid"}

    # Document structure
    sections_identified: list[str]
    has_section_c: bool = False
    has_section_l: bool = False
    has_section_m: bool = False
    has_pws_sow: bool = False

    # Requirements
    total_requirements: int
    compliance_matrix: list[ComplianceMatrixEntry]
    rtm: list[RTMEntry]

    # Submission requirements
    page_limits: Any = Field(default_factory=dict)
    font_requirements: Any = Field(default_factory=dict)
    submission_portal: Optional[str] = None
    submission_format: Optional[str] = None

    # Certifications
    required_certifications: list[str] = Field(default_factory=list)
    vetcert_required: bool = False
    sf_forms_required: list[str] = Field(default_factory=list)

    # Dates
    questions_due: Optional[str] = None
    proposal_due: Optional[str] = None

    # Set-aside specific
    sdvosb_narrative_required: bool = False


def parse_solicitation_document(document_text: str) -> Any:
    """
    Parse solicitation document to identify sections.

    Args:
        document_text: Full text of solicitation document

    Returns:
        Dictionary with identified sections and structure
    """
    sections_found = []
    has_section_c = False
    has_section_l = False
    has_section_m = False
    has_pws_sow = False

    # Look for standard FAR sections
    section_markers = {
        "SECTION C": "has_section_c",
        "PART I - THE SCHEDULE": "has_section_c",
        "SECTION L": "has_section_l",
        "INSTRUCTIONS": "has_section_l",
        "SECTION M": "has_section_m",
        "EVALUATION": "has_section_m",
        "PWS": "has_pws_sow",
        "PERFORMANCE WORK STATEMENT": "has_pws_sow",
        "STATEMENT OF WORK": "has_pws_sow",
        "SOW": "has_pws_sow",
    }

    text_upper = document_text.upper()

    for marker, flag in section_markers.items():
        if marker in text_upper:
            sections_found.append(marker)
            if flag == "has_section_c":
                has_section_c = True
            elif flag == "has_section_l":
                has_section_l = True
            elif flag == "has_section_m":
                has_section_m = True
            elif flag == "has_pws_sow":
                has_pws_sow = True

    return {
        "sections_identified": sections_found,
        "has_section_c": has_section_c,
        "has_section_l": has_section_l,
        "has_section_m": has_section_m,
        "has_pws_sow": has_pws_sow,
    }


def extract_requirements(document_text: str, section: str = "all") -> list[dict]:
    """
    Extract requirements from solicitation document.

    Args:
        document_text: Document text
        section: Which section to extract from (all, pws, section_l, section_c)

    Returns:
        List of requirement dictionaries
    """
    requirements = []

    # Common requirement indicators
    requirement_patterns = [
        "shall",
        "must",
        "will",
        "is required to",
        "the contractor shall",
        "the offeror shall",
    ]

    # Split into sentences
    sentences = document_text.split(".")

    req_id = 1
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        # Check if sentence contains requirement indicators
        sentence_lower = sentence.lower()
        is_requirement = any(pattern in sentence_lower for pattern in requirement_patterns)

        if is_requirement and len(sentence) > 20:  # Filter out short fragments
            requirements.append(
                {
                    "requirement_id": f"REQ-{req_id:04d}",
                    "requirement_text": sentence,
                    "source_section": section,
                }
            )
            req_id += 1

    return requirements


def extract_submission_requirements(document_text: str) -> Any:
    """
    Extract submission requirements (page limits, formats, etc.).

    Args:
        document_text: Document text

    Returns:
        Dictionary with submission requirements
    """
    submission_reqs = {
        "page_limits": {},
        "font_requirements": {},
        "submission_portal": None,
        "submission_format": None,
    }

    text_lower = document_text.lower()

    # Extract page limits
    if "page limit" in text_lower or "page limitation" in text_lower:
        # Common patterns: "technical volume: 50 pages", "not to exceed 25 pages"
        if "technical" in text_lower:
            # Look for number near "technical volume"
            submission_reqs["page_limits"]["technical"] = 50  # Default, should parse
        if "management" in text_lower:
            submission_reqs["page_limits"]["management"] = 25

    # Extract font requirements
    if "times new roman" in text_lower:
        submission_reqs["font_requirements"]["font_family"] = "Times New Roman"
    elif "arial" in text_lower:
        submission_reqs["font_requirements"]["font_family"] = "Arial"

    if "12 point" in text_lower or "12-point" in text_lower:
        submission_reqs["font_requirements"]["font_size"] = 12
    elif "11 point" in text_lower:
        submission_reqs["font_requirements"]["font_size"] = 11

    # Extract submission portal
    if "sam.gov" in text_lower:
        submission_reqs["submission_portal"] = "SAM.gov"
    elif "pia" in text_lower or "procurement integrated" in text_lower:
        submission_reqs["submission_portal"] = "PIA"
    elif "ebuy" in text_lower:
        submission_reqs["submission_portal"] = "eBuy"

    # Extract format
    if "pdf" in text_lower:
        submission_reqs["submission_format"] = "PDF"
    elif "word" in text_lower or ".docx" in text_lower:
        submission_reqs["submission_format"] = "Word"

    return submission_reqs


def identify_required_certifications(
    document_text: str, set_aside: Optional[str] = None
) -> dict[str, Any]:
    """
    Identify required certifications and forms.

    Args:
        document_text: Document text
        set_aside: Set-aside type (SDVOSB, VOSB, SB)

    Returns:
        Dictionary with certification requirements
    """
    certifications = []
    sf_forms = []
    vetcert_required = False
    sdvosb_narrative_required = False

    text_lower = document_text.lower()

    # Check for VetCert requirement
    if set_aside in ["SDVOSB", "VOSB"] and ("vetcert" in text_lower or "vets first" in text_lower):
        vetcert_required = True
        certifications.append("VetCert Documentation")

    # Check for SDVOSB narrative
    if set_aside == "SDVOSB" and (
        "sdvosb" in text_lower and ("narrative" in text_lower or "describe" in text_lower)
    ):
        sdvosb_narrative_required = True

    # Common certifications
    cert_keywords = {
        "reps and certs": "Representations and Certifications",
        "sam registration": "SAM.gov Registration",
        "far 52.204": "FAR 52.204 Certifications",
        "far 52.219": "Small Business Certifications",
        "cybersecurity": "Cybersecurity Certifications",
        "cmmc": "CMMC Certification",
        "iso 27001": "ISO 27001 Certification",
        "soc 2": "SOC 2 Certification",
    }

    for keyword, cert_name in cert_keywords.items():
        if keyword in text_lower:
            certifications.append(cert_name)

    # Common SF forms
    sf_keywords = {
        "sf 1449": "SF 1449 - Solicitation/Contract/Order",
        "sf 30": "SF 30 - Amendment",
        "sf 18": "SF 18 - Request for Quotations",
        "sf 1442": "SF 1442 - Solicitation, Offer and Award",
    }

    for keyword, form_name in sf_keywords.items():
        if keyword in text_lower:
            sf_forms.append(form_name)

    return {
        "required_certifications": certifications,
        "sf_forms_required": sf_forms,
        "vetcert_required": vetcert_required,
        "sdvosb_narrative_required": sdvosb_narrative_required,
    }


def build_compliance_matrix(requirements: list[Any]) -> Any:
    """
    Build compliance matrix from requirements.

    Args:
        requirements: List of extracted requirements

    Returns:
        List of compliance matrix entries
    """
    compliance_matrix = []

    for req in requirements:
        entry = {
            "requirement_id": req["requirement_id"],
            "requirement_text": req["requirement_text"],
            "source_section": req["source_section"],
            "compliance_approach": "To be determined - requires technical analysis",
            "proposal_section": "TBD",
            "status": "pending",
        }
        compliance_matrix.append(entry)

    return compliance_matrix


def build_rtm(requirements: list[Any]) -> Any:
    """
    Build Requirements Traceability Matrix.

    Args:
        requirements: List of extracted requirements

    Returns:
        List of RTM entries
    """
    rtm = []

    for req in requirements:
        entry = {
            "requirement_id": req["requirement_id"],
            "requirement_text": req["requirement_text"],
            "source_document": "Solicitation",
            "source_section": req["source_section"],
            "proposal_section": "TBD",
            "verification_method": "demonstration",  # Default, should be determined per requirement
            "verification_artifact": None,
            "status": "pending",
        }
        rtm.append(entry)

    return rtm


class SolicitationReviewAgent:
    """Solicitation Review Agent for parsing RFPs and building compliance artifacts."""

    def __init__(self) -> None:
        """Initialize Solicitation Review Agent."""
        self.settings = settings
        self.logger = logger
        self.instructions = SOLICITATION_REVIEW_AGENT_INSTRUCTIONS
        self.llm_provider = (
            self.settings.solicitation_review_agent_llm_provider
            or self.settings.default_llm_provider
        )
        self.llm_model = self.settings.solicitation_review_agent_llm_model
        self.llm_temperature = self.settings.openai_temperature

    async def analyze_solicitation(
        self, document_text: str, set_aside: Optional[str] = None
    ) -> SolicitationAnalysis:
        """
        Analyze a solicitation document.

        Args:
            document_text: Full text of solicitation
            set_aside: Set-aside type (SDVOSB, VOSB, SB)

        Returns:
            SolicitationAnalysis with compliance matrix and RTM
        """
        self.logger.info("Analyzing solicitation document")

        text_lower = document_text.lower()

        section_markers = {
            "SECTION C": "section c",
            "SECTION L": "section l",
            "SECTION M": "section m",
            "PERFORMANCE WORK STATEMENT": "performance work statement",
            "STATEMENT OF WORK": "statement of work",
        }
        sections_identified = [
            section for section, marker in section_markers.items() if marker in text_lower
        ]

        requirements = extract_requirements(document_text)
        submission_requirements = extract_submission_requirements(document_text)
        certification_requirements = identify_required_certifications(document_text, set_aside)

        compliance_matrix = build_compliance_matrix(requirements)
        rtm = build_rtm(requirements)

        return SolicitationAnalysis(
            sections_identified=sections_identified,
            has_section_c="SECTION C" in sections_identified,
            has_section_l="SECTION L" in sections_identified,
            has_section_m="SECTION M" in sections_identified,
            has_pws_sow="PERFORMANCE WORK STATEMENT" in sections_identified
            or "STATEMENT OF WORK" in sections_identified,
            total_requirements=len(requirements),
            compliance_matrix=compliance_matrix,
            rtm=rtm,
            page_limits=submission_requirements["page_limits"],
            font_requirements=submission_requirements["font_requirements"],
            submission_portal=submission_requirements["submission_portal"],
            submission_format=submission_requirements["submission_format"],
            required_certifications=certification_requirements["required_certifications"],
            vetcert_required=certification_requirements["vetcert_required"],
            sf_forms_required=certification_requirements["sf_forms_required"],
            sdvosb_narrative_required=certification_requirements["sdvosb_narrative_required"],
        )
