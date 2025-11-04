"""Tests for proposal generation helper behaviour."""

from govcon.agents.proposal_generation import ProposalGenerationAgent


def test_build_knowledge_prompt_formats_and_dedupes() -> None:
    """Ensure knowledge prompt builder formats sections and deduplicates citations."""
    agent = ProposalGenerationAgent(use_knowledge_base=False)

    long_text = "Paragraph " + "A" * 930
    snippet = {
        "title": "Doc 1",
        "score": 0.91,
        "text": long_text,
        "document_id": 7,
        "chunk_index": 0,
    }

    prompt, citations = agent._build_knowledge_prompt(
        [
            ("Section A", [snippet]),
            ("Section B", [snippet]),
        ]
    )

    expected_prefix = long_text[: agent.KNOWLEDGE_SNIPPET_MAX_CHARS]

    assert "Section A" in prompt
    assert "Section B" in prompt
    assert f"{expected_prefix}..." in prompt
    assert "Incorporate the insights above in your own words." in prompt
    assert citations == ["Doc 1 | score=0.91 | doc_id=7 | chunk=0"]
