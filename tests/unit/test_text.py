"""Unit tests for text processing and normalization."""

from graph_intelligence.common.text import (
    extract_keywords,
    normalize_term,
    squash,
    tokenize,
)


def test_normalize_term():
    assert normalize_term("Payment Service") == "payment service"
    assert normalize_term("Payment's Service") == "payment service"
    assert normalize_term("payment-service_v2") == "payment service v2"
    assert normalize_term("retries") == "retry"
    assert normalize_term("dependencies") == "dependency"
    assert normalize_term("services") == "service"
    assert normalize_term("process") == "process"  # 'ss' preserved


def test_squash():
    assert squash("Payment Service") == "paymentservice"
    assert squash("PaymentService") == "paymentservice"
    assert squash("payment-service") == "paymentservice"
    assert squash("INC-PAY-042") == "incpay042"
    assert squash("") == ""


def test_tokenize():
    tokens = tokenize("What did we decide about PaymentService retries and timeouts?")
    assert "decide" in tokens
    assert "paymentservice" in tokens
    assert "retry" in tokens
    assert "timeout" in tokens
    # Stop words must be filtered out
    assert "what" not in tokens
    assert "did" not in tokens
    assert "we" not in tokens
    assert "about" not in tokens
    assert "and" not in tokens


def test_extract_keywords():
    raw = ["falkordb", "mcp", "memory", "general", "falkordb", "test", ""]
    kws = extract_keywords(raw)
    assert "falkordb" in kws
    assert "mcp" in kws
    assert "memory" in kws
    # Deduplication and filler filtering
    assert len([k for k in kws if k == "falkordb"]) == 1
    assert "general" not in kws
    assert "test" not in kws
    assert len(kws) <= 20
