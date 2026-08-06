from app.analyzers.legal_risk import LegalRiskAnalyzer
from app.core.llm import LLMClient
from app.core.runner import Runner


def test_flags_unattributed_accusation():
    text = "Mayor Dupont stole 2 million euros from the city fund."
    analyzer = LegalRiskAnalyzer()
    result = Runner(LLMClient(None, None, "x")).run("d", text, analyzer)
    assert result.mode == "mock"
    cats = {f.payload["category"] for f in result.findings}
    assert "unattributed_accusation" in cats


def test_attribution_suppresses_flag():
    text = "Prosecutors allege the mayor stole funds from the city."
    analyzer = LegalRiskAnalyzer()
    result = Runner(LLMClient(None, None, "x")).run("d", text, analyzer)
    cats = {f.payload["category"] for f in result.findings}
    assert "unattributed_accusation" not in cats


def test_offsets_are_valid():
    text = "Local residents are certainly furious about the worst council ever."
    analyzer = LegalRiskAnalyzer()
    result = Runner(LLMClient(None, None, "x")).run("d", text, analyzer)
    assert result.findings
    for f in result.findings:
        assert text[f.char_start:f.char_end] == f.text


def test_every_flag_has_evidence():
    text = "The fraudster always lies and everyone knows it."
    analyzer = LegalRiskAnalyzer()
    result = Runner(LLMClient(None, None, "x")).run("d", text, analyzer)
    assert result.findings
    for f in result.findings:
        assert f.evidence and f.evidence[0].quote
