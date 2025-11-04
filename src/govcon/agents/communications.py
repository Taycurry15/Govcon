"""Communications Agent - Drafts questions, emails, and capability statements.

This agent implements the Q&A and Communications logic from spec Section 7:
"""

import json
from typing import Any, Optional

from pydantic import BaseModel, Field

from govcon.services.llm import ChatMessage, llm_service
from govcon.utils.config import get_settings
from govcon.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

COMMUNICATIONS_AGENT_INSTRUCTIONS = """Role
    You are the Communications Agent for The Bronze Shield's GovCon AI Pipeline. You transform internal draft information
    into polished, compliant, client-facing communications that advance the capture or proposal effort.

Mission Objectives
    • Protect compliance at all times. Every outbound message must follow solicitation instructions verbatim.
    • Reinforce The Bronze Shield's value proposition, especially SDVOSB/VOSB advantages, without overstating claims.
    • Provide communications leadership can transmit immediately - minimal edits, no placeholders unless explicitly marked.

Authoring Standards
    • Tone: formal federal business correspondence - respectful, confident, and free from slang.
    • Citations: reference exact section/page/paragraph numbers when discussing solicitation content.
    • Accuracy: quote solicitation language where interpretation matters; never invent requirements or commitments.
    • Formatting: use Markdown headings, bullets, and lists exactly as requested; otherwise favor clean paragraphs with
      purposeful emphasis (bold for headings only).
    • Quality: zero spelling or grammar errors; ensure contact details, dates, and document titles align with provided context.

Communication Types
    1. Vendor Questions
        - Include Reference, Question, Rationale, and Proposed Interpretation (when provided).
        - Clarify why the ambiguity obstructs compliance or pricing.
        - Ensure numbering follows the user's sequence.
    2. Cover Letters
        - Address the contracting officer by name/title; cite solicitation number, title, and submission date.
        - Summarize differentiators (technical, management, past performance, SDVOSB credentials).
        - Confirm compliance (volumes submitted, forms, certifications) and invite follow-up.
    3. Submission Emails
        - Supply a subject line and body ready for immediate send.
        - Enumerate attachments with filenames, volume descriptions, and version/date if provided.
        - Request receipt confirmation and provide primary/alternate contacts with phone and email.
    4. Capability Statements (1-2 pages equivalent)
        - Structure: Overview, Core Capabilities, Differentiators, Agency Experience, Contract Vehicles, Past Performance,
          Contact Information, Certifications.
        - Use bullets for capabilities; include quantitative proof points whenever supplied.
    5. Teaming Invitations
        - Lead with opportunity context and submission timeline.
        - Outline proposed teaming structure, workshare expectations, and differentiators for the partner.
        - Close with clear next steps (e.g., request for NDA, capabilities matrix, or call scheduling).

Process Expectations
    • Validate required inputs; if critical data is missing, state assumptions or produce a question list instead of guessing.
    • When user context conflicts, escalate by highlighting the discrepancy before final text.
    • Track deadlines and submission portals when mentioned; surface them prominently.

Output Format
    • Provide a suggested email subject when applicable.
    • Return finalized Markdown text ready to paste, with placeholders only where human input is mandatory (label as
      "[INSERT ...]").
    • End each deliverable with contact block and submission signature guidance if not provided."""


class VendorQuestion(BaseModel):
    """Vendor question for solicitation."""

    model_config = {"extra": "forbid"}

    question_number: int
    section_reference: str
    page_number: Optional[int] = None
    paragraph: Optional[str] = None
    question_text: str
    rationale: str


class CommunicationResult(BaseModel):
    """Result from communication generation."""

    model_config = {"extra": "forbid"}

    communication_type: str
    subject: str
    content: str
    attachments: list[str] = Field(default_factory=list)


def draft_vendor_question(
    section_reference: str,
    ambiguity_description: str,
    proposed_interpretation: Optional[str] = None,
) -> str:
    """
    Draft a vendor question for solicitation clarification.

    Args:
        section_reference: Section/page reference (e.g., "Section L, Page 15, Para 3.2")
        ambiguity_description: Description of the ambiguity
        proposed_interpretation: Optional proposed interpretation

    Returns:
        Formatted vendor question
    """
    question = f"""**Reference**: {section_reference}

**Question**: {ambiguity_description}"""

    if proposed_interpretation:
        question += f"""

**Proposed Interpretation**: {proposed_interpretation}

We request clarification to ensure our proposal fully addresses the Government's requirements."""
    else:
        question += """

We request clarification to ensure our proposal fully addresses the Government's requirements."""

    return question


def draft_cover_letter(
    recipient_name: str,
    recipient_title: str,
    agency: str,
    solicitation_number: str,
    opportunity_title: str,
    company_name: str,
    set_aside: Optional[str] = None,
) -> str:
    """
    Draft cover letter for proposal submission.

    Args:
        recipient_name: Contracting officer name
        recipient_title: Contracting officer title
        agency: Agency name
        solicitation_number: Solicitation number
        opportunity_title: Opportunity title
        company_name: Company name
        set_aside: Set-aside type

    Returns:
        Cover letter text
    """
    from datetime import datetime

    letter = f"""{datetime.today().strftime("%B %d, %Y")}

{recipient_name}
{recipient_title}
{agency}

RE: Proposal Submission - {solicitation_number}
    {opportunity_title}

Dear {recipient_name.split()[-1] if recipient_name else "Sir/Madam"}:

{company_name} is pleased to submit this proposal in response to {solicitation_number}, "{opportunity_title}"."""

    if set_aside in ["SDVOSB", "VOSB"]:
        letter += f""" As a certified {set_aside}, we are uniquely positioned to deliver exceptional value while supporting the Government's veteran employment and small business goals."""

    letter += f"""

We have carefully reviewed all solicitation requirements and confirm that our proposal is fully compliant and responsive. Our solution leverages our proven expertise in delivering mission-critical solutions to federal agencies, backed by a strong record of past performance.

Key highlights of our proposal include:

• Comprehensive technical solution addressing all requirements
• Experienced team with relevant certifications and clearances
• Competitive pricing based on current market rates
• Proven past performance on similar contracts
• Commitment to on-time, on-budget delivery

We understand the critical importance of this requirement to {agency}'s mission and have structured our approach to ensure seamless integration, minimal risk, and maximum value.

All required certifications, representations, and forms are included in the Administrative Volume. Our proposal is submitted in accordance with all instructions in Section L.

Should you have any questions or require additional information, please do not hesitate to contact me at [CONTACT INFO].

Thank you for the opportunity to submit this proposal. We look forward to the possibility of supporting {agency} in this important mission.

Respectfully submitted,

[SIGNATURE BLOCK]
{company_name}
[Contact Information]"""

    return letter


def draft_submission_email(
    solicitation_number: str,
    opportunity_title: str,
    company_name: str,
    file_names: list[str],
) -> str:
    """
    Draft email for proposal submission.

    Args:
        solicitation_number: Solicitation number
        opportunity_title: Opportunity title
        company_name: Company name
        file_names: List of file names being submitted

    Returns:
        Email text
    """
    email = f"""Subject: Proposal Submission - {solicitation_number} - {company_name}

Dear Contracting Officer:

{company_name} hereby submits our proposal in response to {solicitation_number}, "{opportunity_title}".

Our proposal package includes the following files:

"""

    for i, file_name in enumerate(file_names, 1):
        email += f"{i}. {file_name}\n"

    email += f"""

All files have been scanned for viruses and are free from malicious content. The proposal has been reviewed for completeness and compliance with all solicitation requirements.

If you encounter any issues accessing the files or have questions about our submission, please contact us immediately at [CONTACT INFO].

We confirm that this proposal is submitted before the deadline specified in the solicitation and request confirmation of receipt.

Thank you for your consideration.

Respectfully,
{company_name}
[Contact Information]
[Submission Date/Time]"""

    return email


def draft_capability_statement(
    company_name: str,
    set_aside: str,
    core_capabilities: list[str],
    target_agency: str,
    opportunity_focus: str,
) -> str:
    """
    Draft capability statement for Sources Sought or RFI.

    Args:
        company_name: Company name
        set_aside: Set-aside designation
        core_capabilities: List of core capabilities
        target_agency: Target agency
        opportunity_focus: Focus area of opportunity

    Returns:
        Capability statement text
    """
    statement = f"""CAPABILITY STATEMENT

**{company_name}**
{set_aside} | UEI: [UEI] | CAGE: [CAGE]

**Overview**
{company_name} is a {set_aside} with proven expertise in delivering {opportunity_focus} solutions to federal agencies. We specialize in providing innovative, secure, and cost-effective services that enable mission success.

**Core Capabilities**
"""

    for capability in core_capabilities:
        statement += f"• {capability}\n"

    statement += f"""
**Differentiators**
• **{set_aside} Certified**: Supporting federal socioeconomic goals
• **Security-Focused**: CMMC, NIST 800-171, and FedRAMP experience
• **Proven Performance**: Track record of on-time, on-budget delivery
• **Technical Excellence**: Industry-leading certifications and expertise
• **Customer-Centric**: Dedicated to mission success and customer satisfaction

**{target_agency} Experience**
We have successfully supported {target_agency} and similar agencies with:
• IT modernization and cloud migration
• Cybersecurity and zero trust implementation
• Data management and analytics
• Professional services and program management
• Language services and accessibility solutions

**Past Performance Highlights**
• [INSERT RELEVANT CONTRACT 1]
  - Contract Value: $[X]
  - Performance: Excellent ratings, zero defects
  - Relevance: [Brief description]

• [INSERT RELEVANT CONTRACT 2]
  - Contract Value: $[X]
  - Performance: Extended due to exceptional work
  - Relevance: [Brief description]

**Contract Vehicles**
We hold the following contract vehicles:
• [GSA Schedule / IDIQ / BPA if applicable]
• Ready to compete on open market opportunities

**Commitment**
{company_name} is prepared to bring our full capabilities to support {target_agency}'s mission. We welcome the opportunity to discuss how our experience and expertise can address your specific requirements.

**Contact Information**
[Primary Contact]
[Title]
{company_name}
[Email] | [Phone]
[Website]

**Certifications & Registrations**
• {set_aside}
• Active SAM.gov registration
• [Other relevant certifications]

We look forward to the opportunity to support this important requirement."""

    return statement


def draft_teaming_invitation(
    partner_company: str,
    solicitation_number: str,
    opportunity_title: str,
    proposed_role: str,
    company_name: str,
) -> str:
    """
    Draft teaming invitation email.

    Args:
        partner_company: Potential partner company name
        solicitation_number: Solicitation number
        opportunity_title: Opportunity title
        proposed_role: Proposed role for partner (prime/sub)
        company_name: Your company name

    Returns:
        Teaming invitation email
    """
    email = f"""Subject: Teaming Opportunity - {solicitation_number}

Dear [Partner Contact],

{company_name} is pursuing {solicitation_number}, "{opportunity_title}", and we believe {partner_company}'s capabilities would be a valuable addition to our team.

**Opportunity Overview**
We are proposing on this requirement which involves [brief description]. Based on our research and understanding of {partner_company}'s expertise, we see strong alignment with this opportunity.

**Proposed Teaming Structure**
We propose the following structure:
• Prime Contractor: {company_name if proposed_role == "prime" else partner_company}
• Subcontractor: {partner_company if proposed_role == "prime" else company_name}

**Scope of Work**
We envision {partner_company} supporting the following areas:
• [Specific capabilities/tasks]
• [Specific capabilities/tasks]

**Timeline**
• Proposal Due: [DATE]
• Questions Due: [DATE]
• Team Formation: ASAP

**Next Steps**
If {partner_company} is interested in this opportunity, we would like to schedule a call to discuss:

Please let us know your interest by [DATE]. We have a proven track record of successful teaming relationships and are committed to fair and transparent partnerships.

Thank you for considering this opportunity. We look forward to potentially working together.

Best regards,
{company_name}
[Contact Information]"""

    return email


class CommunicationsAgent:
    """Communications Agent for drafting questions, emails, and capability statements."""

    def __init__(self) -> None:
        """Initialize Communications Agent."""
        self.settings = settings
        self.logger = logger
        self.instructions = COMMUNICATIONS_AGENT_INSTRUCTIONS
        self.llm_provider = (
            self.settings.communications_agent_llm_provider or self.settings.default_llm_provider
        )
        self.llm_model = self.settings.communications_agent_llm_model
        self.llm_temperature = self.settings.openai_temperature

    async def draft_communication(
        self, communication_type: str, context: dict[str, Any]
    ) -> CommunicationResult:
        """
        Draft a communication.

        Args:
            communication_type: Type of communication (question, cover_letter, email, capability, teaming)
            context: Context dictionary with required fields

        Returns:
            CommunicationResult with drafted content
        """
        self.logger.info(f"Drafting {communication_type}")

        prompt = self._build_prompt(communication_type, context)
        messages = [
            ChatMessage(role="system", content=self.instructions),
            ChatMessage(role="user", content=prompt),
        ]

        try:
            raw_response = await llm_service.chat(
                messages,
                provider=self.llm_provider,
                model=self.llm_model,
                temperature=self.llm_temperature,
            )
        except Exception as exc:  # pragma: no cover
            self.logger.error("LLM generation failed: %s", exc)
            raise

        parsed = self._parse_llm_response(raw_response, communication_type)

        return CommunicationResult(
            communication_type=communication_type,
            subject=parsed["subject"],
            content=parsed["content"],
            attachments=parsed["attachments"],
        )

    def _build_prompt(self, communication_type: str, context: dict[str, Any]) -> str:
        """Structure the user prompt for the LLM."""
        context_payload = json.dumps(context, indent=2, default=str)
        return (
            "You are drafting a professional federal contracting communication. "
            "Always respond in JSON with keys 'subject', 'content', and 'attachments'. "
            "'content' must be Markdown ready for email delivery. "
            "If attachments are not required, return an empty list. "
            f"Communication type: {communication_type}\n"
            f"Context:\n{context_payload}"
        )

    def _parse_llm_response(self, raw: str, communication_type: str) -> dict[str, Any]:
        """Convert the raw LLM response into a structured payload."""
        fallback_subject = f"{communication_type.replace('_', ' ').title()} Draft"
        fallback = {"subject": fallback_subject, "content": raw.strip(), "attachments": []}

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            self.logger.warning("LLM response was not valid JSON; returning raw content.")
            return fallback

        subject = str(payload.get("subject") or fallback_subject)
        content = str(payload.get("content") or raw.strip())

        attachments_raw = payload.get("attachments") or []
        if isinstance(attachments_raw, list):
            attachments = [str(item) for item in attachments_raw]
        else:
            attachments = [str(attachments_raw)]

        return {"subject": subject, "content": content, "attachments": attachments}
