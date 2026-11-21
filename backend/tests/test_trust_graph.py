from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from app.services.trust_graph import build_trust_graph


def test_graph_has_stable_typed_nodes_edges_and_supplier_concentration():
    business = SimpleNamespace(id="b-1", name="Synthetic Shop")
    source = SimpleNamespace(id="s-1", synthetic=True)
    customer = SimpleNamespace(
        id="cp-customer", business_id="b-1", name="Synthetic Customer",
        type=SimpleNamespace(value="customer"), identifier_masked="GST-XX-1",
    )
    supplier = SimpleNamespace(
        id="cp-supplier", business_id="b-1", name="Synthetic Supplier",
        type=SimpleNamespace(value="supplier"), identifier_masked="GST-XX-2",
    )
    invoice = SimpleNamespace(
        id="inv-1", source_id="s-1", invoice_no="SYN-001", issued_at=date(2025, 7, 1),
        total_inr=Decimal("100000"), counterparty_id="cp-customer",
        status=SimpleNamespace(value="paid"), direction=SimpleNamespace(value="receivable"),
    )
    receipt = SimpleNamespace(
        id="tx-1", source_id="s-1", external_ref="SYN-TX-1", transaction_date=date(2025, 7, 10),
        amount_inr=Decimal("100000"), direction=SimpleNamespace(value="credit"),
        payment_channel=SimpleNamespace(value="bank_transfer"), counterparty_id="cp-customer",
    )
    spend = SimpleNamespace(
        id="tx-2", source_id="s-1", external_ref="SYN-TX-2", transaction_date=date(2025, 7, 11),
        amount_inr=Decimal("50000"), direction=SimpleNamespace(value="debit"),
        payment_channel=SimpleNamespace(value="upi"), counterparty_id="cp-supplier",
    )
    link = SimpleNamespace(
        id="link-1", invoice_id="inv-1", transaction_id="tx-1", source_id="s-1",
        linked_amount_inr=Decimal("100000"), match_method=SimpleNamespace(value="exact_reference"),
        match_status=SimpleNamespace(value="matched"),
    )
    result = build_trust_graph(
        business=business, sources=[source], counterparties=[customer, supplier],
        invoices=[invoice], transactions=[receipt, spend], payment_links=[link],
    )
    assert [node["id"] for node in result["nodes"]] == [
        "business:b-1", "counterparty:cp-customer", "counterparty:cp-supplier",
        "invoice:inv-1", "transaction:tx-1", "transaction:tx-2",
    ]
    assert "MATCHED_TO" in {edge["type"] for edge in result["edges"]}
    supplier_node = next(node for node in result["nodes"] if node["id"] == "counterparty:cp-supplier")
    assert supplier_node["source_ids"] == ["s-1"]
    assert result["metrics"]["top_supplier_share_percent"] == "100.00"
    assert result["provenance"]["synthetic"] is True


def test_unmatched_and_duplicate_findings_use_non_accusatory_wording():
    business = SimpleNamespace(id="b-1", name="Synthetic Shop")
    source = SimpleNamespace(id="s-1", synthetic=True)
    invoice = SimpleNamespace(
        id="inv-1", source_id="s-1", invoice_no="DUP-1", issued_at=date(2025, 7, 1),
        total_inr=Decimal("10"), counterparty_id=None,
        status=SimpleNamespace(value="open"), direction=SimpleNamespace(value="receivable"),
    )
    duplicate = SimpleNamespace(**{**invoice.__dict__, "id": "inv-2"})
    result = build_trust_graph(
        business=business, sources=[source], counterparties=[],
        invoices=[invoice, duplicate], transactions=[], payment_links=[],
    )
    messages = " ".join(item["message"] for item in result["anomalies"])
    assert "fraud conclusion" in messages
    assert "proof of misconduct" in messages
