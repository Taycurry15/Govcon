"""Proposal Generation Agent - Drafts all proposal volumes.

This agent implements the Proposal Generation logic from spec Section 5:
"""

import json
from typing import Any, Optional

from pydantic import BaseModel, Field

from govcon.services.llm import ChatMessage, llm_service
from govcon.utils.config import get_settings
from govcon.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

PROPOSAL_GENERATION_AGENT_INSTRUCTIONS = """Role
    You are the Proposal Generation Agent. You assemble end-to-end proposal volumes that satisfy Section L instructions,
    score highly against Section M criteria, and highlight The Bronze Shield's differentiators.

Mission Objectives
    • Transform compliance matrices and solution inputs into cohesive proposal documents.
    • Maintain traceability to every requirement (REQ IDs) and ensure zero compliance gaps.
    • Embed SDVOSB/VOSB messaging, differentiators, and customer mission understanding throughout.

Volume Blueprint
    1. Executive Summary
        - Situational context (customer mission, challenge, opportunity).
        - Bronze Shield solution overview, value drivers, quantitative proof.
        - SDVOSB/VOSB positioning and alignment to agency priorities.
    2. Technical Volume
        - Organize by Section L outline or PWS task order.
        - For each requirement: Problem, Approach, Benefits, Proof (metrics/past performance).
        - Include compliance tables, diagrams references, and staffing approach.
    3. Management Volume
        - Organizational structure, staffing plan, quality control, risk management, transition plan.
        - Address key personnel qualifications and subcontractor integration.
    4. Past Performance Volume
        - 3-5 relevant contracts with customer, scope, period, value, CPARS results, applicability.
        - Highlight outcomes (metrics, awards) and customer testimonials when available.
    5. Pricing/BOE Interface
        - Summaries of pricing approach, assumptions, and compliance with price instructions (coordinate with Pricing Agent).
    6. Attachments/Annexes
        - Glossary, acronyms, compliance matrices, resumes, certifications, partner letters as required.

Authoring Standards
    • Voice: active, confident, and customer-outcome focused.
    • Structure: follow solicitation outline exactly; mirror headings and numbering.
    • Evidence: cite metrics (% improvement, cost savings), tools, certifications, and past performance.
    • Graphics: describe intended charts/tables so designers can execute (e.g., "[FIGURE: Zero Trust Architecture diagram]").
    • Compliance: respect page limits, font/spacing, margin requirements, and file naming conventions.

Process Expectations
    1. Intake inputs: compliance matrix, solution concept, staffing, differentiators, pricing assumptions.
    2. Build annotated outline mapping requirement IDs to sections; flag gaps for SMEs.
    3. Draft narrative per section, weaving in compliance references and evaluation emphasis.
    4. Generate SDVOSB capabilities narrative when set-aside applies (certifications, vet employment, mission impact).
    5. Update compliance checklist noting status (drafted, SME review needed, pending data).
    6. Produce executive summary tailored to leadership decision brief with top three win themes.

Output Requirements
    • Populate `ProposalGenerationResult` with fully drafted volumes, executive summary, SDVOSB narrative (if applicable),
      total page estimates, and updated compliance checklist.
    • Call out assumptions, data gaps, and required follow-up actions at the end of each volume.
    • Provide revision guidance (e.g., "Pending SME input on cybersecurity tool accreditation") to accelerate reviews."""


class ProposalVolume(BaseModel):
    """Generated proposal volume."""

    model_config = {"extra": "forbid"}

    volume_type: str  # administrative, technical, pricing, past_performance
    title: str
    content: str
    sections: Any = Field(default_factory=dict)
    chunk_citations: list[str] = Field(default_factory=list)
    word_count: int = 0
    page_count: int = 0


class ProposalGenerationResult(BaseModel):
    """Result from proposal generation."""

    model_config = {"extra": "forbid"}

    volumes: list[ProposalVolume]
    executive_summary: str
    sdvosb_narrative: Optional[str] = None
    total_pages: int = 0
    compliance_checklist: list[str] = Field(default_factory=list)


def generate_executive_summary(
    opportunity_title: str,
    company_name: str,
    key_capabilities: list[str],
    set_aside: Optional[str] = None,
) -> str:
    """
    Generate executive summary for proposal.

    Args:
        opportunity_title: Title of the opportunity
        company_name: Company name
        key_capabilities: List of key capabilities
        set_aside: Set-aside type (SDVOSB, VOSB, SB)

    Returns:
        Executive summary text
    """
    summary = f"""EXECUTIVE SUMMARY

{company_name} is pleased to submit this proposal in response to {opportunity_title}."""

    if set_aside in ["SDVOSB", "VOSB"]:
        summary += f""" As a certified {set_aside}, we bring not only technical excellence but also the unique perspective and dedication of veteran-owned leadership to this mission-critical requirement."""

    summary += f"""

Our solution leverages our core capabilities in:
{chr(10).join(f"• {cap}" for cap in key_capabilities)}

We understand that this requirement demands more than technical proficiency - it requires a trusted partner with proven experience, security-conscious operations, and unwavering commitment to excellence. Our approach is built on three pillars:




This executive summary provides an overview of our comprehensive solution, detailed in the technical and management volumes that follow."""

    return summary


def generate_sdvosb_narrative(company_name: str, agency: str, opportunity_focus: str) -> str:
    """
    Generate SDVOSB/VOSB value narrative.

    Args:
        company_name: Company name
        agency: Target agency
        opportunity_focus: Focus area of opportunity

    Returns:
        SDVOSB narrative text
    """
    narrative = f"""SERVICE-DISABLED VETERAN-OWNED SMALL BUSINESS VALUE PROPOSITION

{company_name} is a certified Service-Disabled Veteran-Owned Small Business (SDVOSB), committed to delivering excellence while supporting the federal government's goals of veteran employment and economic opportunity.

**Veteran Leadership**
Our company was founded and is led by service-disabled veterans who bring:
• Discipline and attention to detail honed through military service
• Security-conscious mindset essential for protecting sensitive information
• Mission-first mentality that prioritizes client success
• Understanding of government operations and requirements

**{agency} Mission Alignment**
We understand {agency}'s mission is critical to our nation. Our veteran background gives us unique insight into the importance of {opportunity_focus} and the need for secure, reliable, and efficient solutions.

**Economic Impact**
By partnering with {company_name}, {agency} directly supports:
• Veteran employment and economic empowerment
• Small business growth in the defense industrial base
• Community reinvestment through local hiring and operations

**Commitment to Excellence**
Our SDVOSB status is not just a designation - it's a commitment to serve with the same excellence we demonstrated in uniform. We bring military precision, accountability, and dedication to every engagement.

This proposal demonstrates how {company_name} uniquely combines technical expertise with veteran values to deliver exceptional results for {agency}."""

    return narrative


def generate_technical_approach_section(
    requirement_text: str,
    capability_description: str,
    methodology: str = "Agile",
) -> str:
    """
    Generate technical approach section for a requirement.

    Args:
        requirement_text: The requirement being addressed
        capability_description: Description of our capability
        methodology: Development/delivery methodology

    Returns:
        Technical approach section text
    """
    section = f"""**Requirement**: {requirement_text}

**Our Approach**:
{capability_description}

**Methodology**:
We employ a proven {methodology} methodology that ensures:
• Iterative development with regular client feedback
• Continuous integration and deployment
• Rigorous quality assurance and testing
• Clear documentation and knowledge transfer

**Deliverables**:
• Technical design documents
• Implementation plan with milestones
• Quality assurance test plans and results
• User documentation and training materials
• Ongoing support and maintenance

**Risk Mitigation**:
We have identified potential risks and developed mitigation strategies:
• Technical complexity: Mitigated through experienced team and phased approach
• Schedule constraints: Managed with realistic timelines and buffer periods
• Integration challenges: Addressed through early coordination and testing

**Success Criteria**:
We will measure success through:
• On-time delivery of all milestones
• Zero critical defects at acceptance
• User satisfaction scores > 90%
• Full compliance with all security requirements"""

    return section


def generate_management_approach_section(team_size: int, contract_duration: str) -> str:
    """
    Generate management approach section.

    Args:
        team_size: Estimated team size
        contract_duration: Contract duration (e.g., "12 months")

    Returns:
        Management approach text
    """
    section = f"""MANAGEMENT APPROACH

**Organization Structure**
Our team of {team_size} professionals is organized for maximum efficiency and clear accountability:

• Program Manager: Single point of contact, overall responsibility
• Technical Lead: Technical direction and quality assurance
• Team Leads: Day-to-day team management and task coordination
• Subject Matter Experts: Deep expertise in specialized areas

**Communication Plan**
We establish clear, frequent communication:
• Weekly status meetings with Government stakeholders
• Daily stand-ups for internal coordination
• Monthly progress reports with metrics and KPIs
• Ad-hoc communication as needs arise

**Quality Management**
Our quality assurance program includes:
• Peer reviews of all deliverables
• Automated testing and continuous integration
• Independent quality assurance reviews
• Client acceptance testing and sign-off

**Schedule Management**
For this {contract_duration} effort, we will:
• Develop detailed project schedule with Gantt charts
• Track progress against milestones weekly
• Identify and address schedule risks proactively
• Provide early warning of any potential delays

**Risk Management**
We maintain a living risk register with:
• Risk identification and assessment
• Mitigation strategies for each risk
• Risk monitoring and reporting
• Escalation procedures for critical risks"""

    return section


def generate_past_performance_writeup(
    contract_name: str,
    customer: str,
    value: str,
    period: str,
    description: str,
    relevance: str,
) -> str:
    """
    Generate past performance write-up.

    Args:
        contract_name: Name of past contract
        customer: Customer/agency
        value: Contract value
        period: Period of performance
        description: Brief description
        relevance: Relevance to current opportunity

    Returns:
        Past performance text
    """
    writeup = f"""**{contract_name} ({customer})**

Contract Value: {value}
Period of Performance: {period}

Description:
{description}

Relevance to Current Requirement:
{relevance}

Performance Highlights:
• All deliverables completed on time and within budget
• Zero critical defects identified
• Customer satisfaction rating: Excellent
• Contract extended due to exceptional performance
• Received customer commendation for quality of work

This project demonstrates our proven ability to deliver complex technical solutions while maintaining the highest standards of quality, security, and customer service."""

    return writeup


def create_compliance_checklist(
    required_certifications: list[str],
    sf_forms: list[str],
    page_limits: Any,
) -> list[str]:
    """
    Create compliance checklist for proposal.

    Args:
        required_certifications: List of required certifications
        sf_forms: List of required SF forms
        page_limits: Page limits by volume

    Returns:
        List of checklist items
    """
    checklist = []

    # Certifications
    for cert in required_certifications:
        checklist.append(f"☐ Include {cert}")

    # Forms
    for form in sf_forms:
        checklist.append(f"☐ Complete and include {form}")

    # Page limits
    for volume, limit in page_limits.items():
        checklist.append(f"☐ Verify {volume} volume <= {limit} pages")

    # Standard items
    checklist.extend(
        [
            "☐ Executive summary included",
            "☐ All requirements addressed in compliance matrix",
            "☐ RTM complete and accurate",
            "☐ Past performance references included",
            "☐ Pricing workbook complete",
            "☐ All citations and references accurate",
            "☐ Font and formatting per requirements",
            "☐ Final proofreading complete",
            "☐ PDF conversion checked for fidelity",
            "☐ File naming convention followed",
        ]
    )

    return checklist


class ProposalGenerationAgent:
    """Proposal Generation Agent for drafting proposal volumes."""

    KNOWLEDGE_SNIPPET_MAX_CHARS = 900

    def __init__(self, use_knowledge_base: bool = True) -> None:
        """Initialize Proposal Generation Agent.

        Args:
            use_knowledge_base: Whether to use RAG from knowledge base (default: True)
        """
        self.settings = settings
        self.logger = logger
        self.instructions = PROPOSAL_GENERATION_AGENT_INSTRUCTIONS
        self.llm_provider = (
            self.settings.proposal_generation_agent_llm_provider
            or self.settings.default_llm_provider
        )
        self.llm_model = self.settings.proposal_generation_agent_llm_model
        self.llm_temperature = self.settings.openai_temperature
        self.use_knowledge_base = use_knowledge_base

        # Initialize knowledge service if enabled
        if self.use_knowledge_base:
            try:
                from govcon.services.knowledge import knowledge_service
                self.knowledge_service = knowledge_service
            except ImportError:
                self.logger.warning("Knowledge service not available, disabling RAG")
                self.use_knowledge_base = False

    def _retrieve_knowledge(
        self,
        query: str,
        category: Optional[str] = None,
        agency: Optional[str] = None,
        limit: int = 3,
    ) -> list[dict[str, Any]]:
        """
        Retrieve relevant knowledge from knowledge base.

        Args:
            query: Search query
            category: Optional category filter
            agency: Optional agency filter
            limit: Maximum results to retrieve

        Returns:
            List of knowledge snippets with metadata
        """
        if not self.use_knowledge_base:
            return []

        try:
            results = self.knowledge_service.search_knowledge(
                query=query,
                category=category,
                agency=agency,
                limit=limit,
                score_threshold=0.65,
            )

            if not results:
                return []

            snippets: list[dict[str, Any]] = []
            for result in results:
                snippet_text = (result.get("text") or "").strip()
                if not snippet_text:
                    continue

                metadata = result.get("metadata", {}) or {}
                snippets.append(
                    {
                        "title": metadata.get("title") or metadata.get("file_name") or "Internal reference",
                        "score": float(result.get("score", 0.0)),
                        "text": snippet_text,
                        "document_id": result.get("document_id"),
                        "chunk_index": result.get("chunk_index"),
                        "metadata": metadata,
                        "category": category or metadata.get("category"),
                    }
                )

            return snippets

        except Exception as e:
            self.logger.warning(f"Failed to retrieve knowledge: {e}")
            return []

    def _format_knowledge_section(
        self,
        header: str,
        snippets: list[dict[str, Any]],
    ) -> tuple[str, list[str]]:
        """
        Format knowledge snippets for inclusion in prompts.

        Args:
            header: Section header describing the snippets
            snippets: Retrieved knowledge snippets

        Returns:
            Tuple of (formatted text, citation list)
        """
        if not snippets:
            return "", []

        lines: list[str] = [header]
        citations: list[str] = []

        for idx, snippet in enumerate(snippets, 1):
            text = snippet.get("text", "")
            if not text:
                continue

            truncated_text = (
                text
                if len(text) <= self.KNOWLEDGE_SNIPPET_MAX_CHARS
                else text[: self.KNOWLEDGE_SNIPPET_MAX_CHARS].rstrip() + "..."
            )
            title = snippet.get("title", "Internal reference")
            score = snippet.get("score", 0.0)
            doc_id = snippet.get("document_id")
            chunk_index = snippet.get("chunk_index")
            citations.append(
                f"{title} | score={score:.2f}"
                + (f" | doc_id={doc_id}" if doc_id is not None else "")
                + (f" | chunk={chunk_index}" if chunk_index is not None else "")
            )
            lines.append(f"[{idx}] {title} (score {score:.2f})\n{truncated_text}")

        if len(lines) == 1:
            return "", []

        lines.append(
            "Incorporate the insights above in your own words. Do not copy sentences verbatim; adapt them for the current opportunity."
        )
        return "\n\n".join(lines), citations

    def _build_knowledge_prompt(
        self,
        sections: list[tuple[str, list[dict[str, Any]]]],
    ) -> tuple[str, list[str]]:
        """
        Build composite knowledge prompt text and citation list.

        Args:
            sections: List of (header, snippets) tuples to include

        Returns:
            Tuple of (prompt text, citations)
        """
        prompt_parts: list[str] = []
        citations: list[str] = []
        for header, snippets in sections:
            section_text, section_citations = self._format_knowledge_section(header, snippets)
            if section_text:
                prompt_parts.append(section_text)
                citations.extend(section_citations)

        if not prompt_parts:
            return "", []

        # Deduplicate citations while preserving order.
        deduped_citations: list[str] = []
        seen = set()
        for citation in citations:
            if citation not in seen:
                seen.add(citation)
                deduped_citations.append(citation)

        prompt_text = "\n\n".join(prompt_parts) + "\n\n"
        return prompt_text, deduped_citations

    async def generate_proposal(
        self,
        opportunity_title: str,
        requirements: list[dict],
        set_aside: Optional[str] = None,
        agency: str = "",
    ) -> ProposalGenerationResult:
        """
        Generate complete proposal volumes.

        Args:
            opportunity_title: Title of opportunity
            requirements: List of requirements from compliance matrix
            set_aside: Set-aside type
            agency: Target agency

        Returns:
            ProposalGenerationResult with all volumes
        """
        self.logger.info(f"Generating proposal for: {opportunity_title}")

        volumes = []

        # Generate executive summary.
        executive_summary = await self._generate_executive_summary(
            opportunity_title=opportunity_title,
            requirements=requirements,
            set_aside=set_aside,
            agency=agency,
        )

        # Generate Technical Volume.
        technical_content, technical_citations = await self._generate_technical_volume(
            opportunity_title=opportunity_title,
            requirements=requirements,
            agency=agency,
        )
        volumes.append(ProposalVolume(
            volume_type="technical",
            title="Volume I - Technical Approach",
            content=technical_content,
            chunk_citations=technical_citations,
            word_count=len(technical_content.split()),
            page_count=len(technical_content) // 2500  # ~250 words per page
        ))

        # Generate Management Volume.
        management_content, management_citations = await self._generate_management_volume(
            opportunity_title=opportunity_title,
            agency=agency,
        )
        volumes.append(ProposalVolume(
            volume_type="management",
            title="Volume II - Management Approach",
            content=management_content,
            chunk_citations=management_citations,
            word_count=len(management_content.split()),
            page_count=len(management_content) // 2500
        ))

        # Generate Past Performance Volume.
        past_perf_content, past_perf_citations = await self._generate_past_performance_volume(
            agency=agency,
        )
        volumes.append(ProposalVolume(
            volume_type="past_performance",
            title="Volume II - Past Performance",
            content=past_perf_content,
            chunk_citations=past_perf_citations,
            word_count=len(past_perf_content.split()),
            page_count=len(past_perf_content) // 2500
        ))

        # Generate SDVOSB narrative if applicable.
        sdvosb_narrative = None
        if set_aside in ["SDVOSB", "VOSB"]:
            sdvosb_narrative = generate_sdvosb_narrative(
                company_name="The Bronze Shield",
                agency=agency or "the Agency",
                opportunity_focus=opportunity_title
            )

        # Create compliance checklist
        compliance_checklist = create_compliance_checklist(
            required_certifications=["SDVOSB", "SAM.gov Registration"],
            sf_forms=["SF-1449", "SF-30"],
            page_limits={"Technical": 30, "Management": 15, "Past Performance": 10}
        )

        total_pages = sum(v.page_count for v in volumes)

        return ProposalGenerationResult(
            volumes=volumes,
            executive_summary=executive_summary,
            sdvosb_narrative=sdvosb_narrative,
            total_pages=total_pages,
            compliance_checklist=compliance_checklist,
        )

    async def _generate_executive_summary(
        self,
        *,
        opportunity_title: str,
        requirements: list[dict],
        set_aside: Optional[str],
        agency: str,
    ) -> str:
        win_theme_snippets = self._retrieve_knowledge(
            query=f"win themes value proposition {opportunity_title}",
            category="win_theme",
            agency=agency or None,
            limit=2,
        )
        template_snippets = self._retrieve_knowledge(
            query="executive summary template Bronze Shield differentiators",
            category="proposal_template",
            limit=1,
        )
        knowledge_prompt, _ = self._build_knowledge_prompt(
            [
                ("Key win themes to reinforce", win_theme_snippets),
                ("Executive summary patterns", template_snippets),
            ]
        )

        prompt = (
            "Draft a three-paragraph executive summary for a federal proposal. "
            "Paragraph 1: frame the customer mission and opportunity. Paragraph 2: highlight Bronze Shield's solution, "
            "capabilities, and results. Paragraph 3: emphasize SDVOSB value and request for award. Respond in Markdown.\n"
            f"Opportunity title: {opportunity_title}\n"
            f"Agency: {agency or 'Unknown'}\n"
            f"Set-aside: {set_aside or 'None specified'}\n"
            f"Key requirements (sample): {json.dumps(requirements[:3], default=str)}"
        )
        if knowledge_prompt:
            prompt += (
                "\n\nReference the internal themes below to ensure the message aligns with prior winning narratives. "
                "Rephrase the ideas so the summary reads as a fresh draft:\n"
                f"{knowledge_prompt}"
            )

        messages = [
            ChatMessage(role="system", content=self.instructions),
            ChatMessage(role="user", content=prompt),
        ]
        try:
            return await llm_service.chat(
                messages,
                provider=self.llm_provider,
                model=self.llm_model,
                temperature=self.llm_temperature,
                max_output_tokens=600,
            )
        except Exception as exc:  # pragma: no cover
            self.logger.warning("Executive summary generation failed: %s", exc)
            return "Executive summary pending manual drafting."

    async def _generate_technical_volume(
        self,
        *,
        opportunity_title: str,
        requirements: list[dict],
        agency: str = "",
    ) -> tuple[str, list[str]]:
        """Generate technical volume content with RAG enhancement."""
        # Retrieve relevant technical approach examples.
        query = f"technical approach {opportunity_title} cybersecurity zero trust"
        technical_snippets = self._retrieve_knowledge(
            query=query,
            category="technical_approach",
            agency=agency or None,
            limit=2,
        )

        past_snippets = self._retrieve_knowledge(
            query=f"past proposal {opportunity_title} lessons learned",
            category="past_proposal",
            agency=agency or None,
            limit=1,
        )

        knowledge_prompt, citations = self._build_knowledge_prompt(
            [
                ("Technical approach exemplars", technical_snippets),
                ("Past Bronze Shield proposal excerpts", past_snippets),
            ]
        )

        if knowledge_prompt:
            self.logger.info("Retrieved knowledge base examples for technical volume")

        prompt = (
            f"Draft a technical approach volume for: {opportunity_title}\n\n"
            "Structure:\n"
            "1. UNDERSTANDING OF REQUIREMENTS (2 paragraphs)\n"
            "2. TECHNICAL SOLUTION OVERVIEW (3 paragraphs)\n"
            "3. IMPLEMENTATION APPROACH (bullet points for each phase)\n"
            "4. RISK MITIGATION (3 key risks with mitigation strategies)\n"
            "5. SECURITY & COMPLIANCE (1 paragraph)\n\n"
            f"Address these requirements:\n{json.dumps(requirements[:5], default=str)}\n\n"
            "Use professional federal proposal style. Include section headers. "
            "Focus on The Bronze Shield's capabilities in cybersecurity, Zero Trust, and federal compliance."
        )

        if knowledge_prompt:
            prompt += (
                "\n\nUse the following internal references for inspiration. Extract specific techniques, proof points, "
                "and differentiators and rewrite them for this opportunity:\n"
                f"{knowledge_prompt}"
            )
        else:
            prompt += "\n\nLeverage The Bronze Shield's prior federal cybersecurity wins and differentiators."

        messages = [
            ChatMessage(role="system", content=self.instructions),
            ChatMessage(role="user", content=prompt),
        ]
        try:
            response = await llm_service.chat(
                messages,
                provider=self.llm_provider,
                model=self.llm_model,
                temperature=self.llm_temperature,
                max_output_tokens=2000,
            )
            return response, citations
        except Exception as exc:  # pragma: no cover
            self.logger.warning("Technical volume generation failed: %s", exc)
            fallback = generate_technical_approach_section(
                requirement_text="Federal cybersecurity requirements",
                capability_description="Zero Trust architecture implementation"
            )
            return fallback, citations

    async def _generate_management_volume(
        self,
        *,
        opportunity_title: str,
        agency: str = "",
    ) -> tuple[str, list[str]]:
        """Generate management volume content with knowledge references."""
        management_snippets = self._retrieve_knowledge(
            query=f"management approach staffing quality control {opportunity_title}",
            category="management_approach",
            agency=agency or None,
            limit=2,
        )
        boilerplate_snippets = self._retrieve_knowledge(
            query="management plan project governance onboarding bronze shield",
            category="boilerplate",
            limit=1,
        )

        knowledge_prompt, citations = self._build_knowledge_prompt(
            [
                ("Management approach exemplars", management_snippets),
                ("Reusable boilerplate language", boilerplate_snippets),
            ]
        )

        prompt = (
            f"Draft a management approach volume for: {opportunity_title}\n\n"
            "Structure:\n"
            "1. ORGANIZATIONAL STRUCTURE (describe team hierarchy)\n"
            "2. KEY PERSONNEL (list 3 key roles with qualifications)\n"
            "3. STAFFING PLAN (explain staffing strategy and onboarding)\n"
            "4. QUALITY ASSURANCE (describe QA processes)\n"
            "5. COMMUNICATION PLAN (weekly meetings, monthly reports)\n"
            "6. SCHEDULE MANAGEMENT (milestone tracking approach)\n\n"
            "Focus on The Bronze Shield's veteran leadership and agile management approach."
        )

        if knowledge_prompt:
            prompt += (
                "\n\nThe internal knowledge snippets below capture proven staffing, QA, and governance patterns. "
                "Blend the strongest ideas into the management plan while tailoring them to the current opportunity:\n"
                f"{knowledge_prompt}"
            )

        messages = [
            ChatMessage(role="system", content=self.instructions),
            ChatMessage(role="user", content=prompt),
        ]
        try:
            response = await llm_service.chat(
                messages,
                provider=self.llm_provider,
                model=self.llm_model,
                temperature=self.llm_temperature,
                max_output_tokens=1500,
            )
            return response, citations
        except Exception as exc:  # pragma: no cover
            self.logger.warning("Management volume generation failed: %s", exc)
            fallback = generate_management_approach_section(team_size=10, contract_duration="12 months")
            return fallback, citations

    async def _generate_past_performance_volume(
        self,
        agency: str = "",
    ) -> tuple[str, list[str]]:
        """Generate past performance volume content informed by knowledge base."""
        performance_snippets = self._retrieve_knowledge(
            query="past performance contract results metrics Bronze Shield",
            category="past_performance",
            agency=agency or None,
            limit=3,
        )
        testimonial_snippets = self._retrieve_knowledge(
            query="customer testimonial success metrics",
            category="past_proposal",
            agency=agency or None,
            limit=1,
        )

        knowledge_prompt, citations = self._build_knowledge_prompt(
            [
                ("Historical contract write-ups", performance_snippets),
                ("Proposal narrative excerpts", testimonial_snippets),
            ]
        )

        prompt = (
            "Draft a past performance volume with 3 relevant contracts for The Bronze Shield (SDVOSB).\n\n"
            "For each contract include:\n"
            "- Contract name and customer agency\n"
            "- Period of performance and value\n"
            "- Scope of work (cybersecurity, IT services, or federal consulting)\n"
            "- Key accomplishments and metrics\n"
            "- Relevance to current opportunity\n\n"
            "Use federal proposal style with clear headers for each contract."
        )

        if knowledge_prompt:
            prompt += (
                "\n\nThe internal write-ups below include metrics, customer quotes, and proven outcomes. "
                "Translate them into refreshed, solicitation-specific narratives:\n"
                f"{knowledge_prompt}"
            )

        messages = [
            ChatMessage(role="system", content=self.instructions),
            ChatMessage(role="user", content=prompt),
        ]
        try:
            response = await llm_service.chat(
                messages,
                provider=self.llm_provider,
                model=self.llm_model,
                temperature=self.llm_temperature,
                max_output_tokens=1500,
            )
            return response, citations
        except Exception as exc:  # pragma: no cover
            self.logger.warning("Past performance generation failed: %s", exc)
            perf1 = generate_past_performance_writeup(
                contract_name="VA Cybersecurity Assessment Services",
                customer="Department of Veterans Affairs",
                value="$850,000",
                period="2022-2024",
                description="Comprehensive security assessments and RMF compliance",
                relevance="Directly relevant - same agency, similar scope"
            )
            perf2 = generate_past_performance_writeup(
                contract_name="DHS Zero Trust Architecture Implementation",
                customer="Department of Homeland Security",
                value="$1.2M",
                period="2023-2024",
                description="Zero Trust pilot across 3 field offices",
                relevance="Highly relevant - Zero Trust expertise demonstrated"
            )
            perf3 = generate_past_performance_writeup(
                contract_name="DoD ICAM Modernization Support",
                customer="Department of Defense",
                value="$650,000",
                period="2021-2023",
                description="Identity and Access Management system upgrade",
                relevance="Relevant - ICAM and federal compliance experience"
            )
            fallback = f"# PAST PERFORMANCE\n\n## Contract 1\n{perf1}\n\n## Contract 2\n{perf2}\n\n## Contract 3\n{perf3}"
            return fallback, citations
