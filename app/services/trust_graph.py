from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any, Iterable

import networkx as nx

GRAPH_RULE_VERSION = "trust-graph.v1"


def _money(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


def _node(node_id: str, node_type: str, label: str, source_ids: Iterable[str] = (), **attrs: Any) -> dict[str, Any]:
    return {
        "id": node_id,
        "type": node_type,
        "label": label,
        "source_ids": sorted(set(source_ids)),
        **attrs,
    }


def _edge(edge_id: str, source: str, target: str, edge_type: str, source_ids: Iterable[str], **attrs: Any) -> dict[str, Any]:
    return {
        "id": edge_id,
        "source": source,
        "target": target,
        "type": edge_type,
        "source_ids": sorted(set(source_ids)),
        **attrs,
    }


def _enum_value(value):
    return getattr(value, "value", value)


def build_trust_graph(
    *,
    business: Any,
    sources: Iterable[Any],
    counterparties: Iterable[Any],
    invoices: Iterable[Any],
    transactions: Iterable[Any],
    payment_links: Iterable[Any],
) -> dict[str, Any]:
    """Build a bounded, auditable NetworkX graph from database records."""
    sources = list(sources)
    counterparties = list(counterparties)
    invoices = list(invoices)
    transactions = list(transactions)
    payment_links = list(payment_links)
    source_by_id = {source.id: source for source in sources}
    counterparty_sources: dict[str, set[str]] = defaultdict(set)
    for record in (*invoices, *transactions):
        if record.counterparty_id:
            counterparty_sources[record.counterparty_id].add(record.source_id)
    graph = nx.MultiDiGraph()
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    anomalies: list[dict[str, Any]] = []

    business_id = f"business:{business.id}"
    business_node = _node(business_id, "Business", business.name, **{"business_id": business.id})
    graph.add_node(business_id, **business_node)
    nodes.append(business_node)

    for counterparty in counterparties:
        observed_sources = counterparty_sources[counterparty.id]
        directory_source = getattr(counterparty, "source_id", None)
        sources_for_node = observed_sources | ({directory_source} if directory_source in source_by_id else set())
        node_id = f"counterparty:{counterparty.id}"
        node = _node(
            node_id,
            "Counterparty",
            counterparty.name,
            sources_for_node,
            counterparty_id=counterparty.id,
            counterparty_type=_enum_value(counterparty.type),
            identifier_masked=counterparty.identifier_masked,
        )
        graph.add_node(node_id, **node)
        nodes.append(node)
        if directory_source and not observed_sources:
            edge_type = "LISTED_SUPPLIER"
        else:
            edge_type = "PURCHASED_FROM" if _enum_value(counterparty.type) == "supplier" else "SOLD_TO"
        edge = _edge(
            f"edge:{edge_type.lower()}:{business.id}:{counterparty.id}",
            business_id,
            node_id,
            edge_type,
            sources_for_node,
            verification_status="uploaded-only",
        )
        graph.add_edge(business_id, node_id, key=edge["id"], **edge)
        edges.append(edge)

    invoice_by_id = {invoice.id: invoice for invoice in invoices}
    transaction_by_id = {transaction.id: transaction for transaction in transactions}
    for invoice in invoices:
        node_id = f"invoice:{invoice.id}"
        node = _node(
            node_id,
            "Invoice",
            invoice.invoice_no,
            [invoice.source_id],
            invoice_id=invoice.id,
            amount_inr=_money(invoice.total_inr),
            date=invoice.issued_at.isoformat(),
            counterparty_id=invoice.counterparty_id,
            status=_enum_value(invoice.status),
        )
        graph.add_node(node_id, **node)
        nodes.append(node)
        edge = _edge(
            f"edge:invoiced:{invoice.id}",
            business_id,
            node_id,
            "INVOICED",
            [invoice.source_id],
            amount_inr=_money(invoice.total_inr),
            date=invoice.issued_at.isoformat(),
            verification_status="uploaded-only",
        )
        graph.add_edge(business_id, node_id, key=edge["id"], **edge)
        edges.append(edge)

    for transaction in transactions:
        node_id = f"transaction:{transaction.id}"
        node = _node(
            node_id,
            "Transaction",
            transaction.external_ref,
            [transaction.source_id],
            transaction_id=transaction.id,
            amount_inr=_money(transaction.amount_inr),
            date=transaction.transaction_date.isoformat(),
            direction=_enum_value(transaction.direction),
            payment_channel=_enum_value(transaction.payment_channel),
            counterparty_id=transaction.counterparty_id,
        )
        graph.add_node(node_id, **node)
        nodes.append(node)
        edge = _edge(
            f"edge:paid:{transaction.id}",
            business_id,
            node_id,
            "PAID",
            [transaction.source_id],
            amount_inr=_money(transaction.amount_inr),
            date=transaction.transaction_date.isoformat(),
            verification_status="uploaded-only",
        )
        graph.add_edge(business_id, node_id, key=edge["id"], **edge)
        edges.append(edge)

    linked_invoice_ids: set[str] = set()
    linked_transaction_ids: set[str] = set()
    for link in payment_links:
        if link.invoice_id not in invoice_by_id or link.transaction_id not in transaction_by_id:
            continue
        linked_invoice_ids.add(link.invoice_id)
        linked_transaction_ids.add(link.transaction_id)
        edge = _edge(
            f"edge:matched:{link.id}",
            f"invoice:{link.invoice_id}",
            f"transaction:{link.transaction_id}",
            "MATCHED_TO",
            [invoice_by_id[link.invoice_id].source_id, transaction_by_id[link.transaction_id].source_id],
            amount_inr=_money(link.linked_amount_inr),
            match_method=_enum_value(link.match_method),
            match_status=_enum_value(link.match_status),
            verification_status="cross-source-consistent" if _enum_value(link.match_status) == "matched" else _enum_value(link.match_status),
        )
        graph.add_edge(edge["source"], edge["target"], key=edge["id"], **edge)
        edges.append(edge)

    for invoice in invoices:
        if _enum_value(invoice.direction) == "receivable" and invoice.id not in linked_invoice_ids:
            anomalies.append({
                "code": "UNMATCHED_INVOICE",
                "severity": "medium",
                "message": "Invoice has no linked payment in the available records; this is an evidence gap, not a fraud conclusion.",
                "record_ids": [invoice.id],
                "source_ids": [invoice.source_id],
                "amounts_inr": [_money(invoice.total_inr)],
                "check": "No PaymentLink was present for this invoice.",
                "recommended_follow_up": "Request the payment source or document why it remains open.",
            })
    for transaction in transactions:
        if _enum_value(transaction.direction) == "credit" and transaction.id not in linked_transaction_ids:
            anomalies.append({
                "code": "UNMATCHED_PAYMENT",
                "severity": "medium",
                "message": "Receipt has no linked invoice in the available records; this is an evidence gap, not a fraud conclusion.",
                "record_ids": [transaction.id],
                "source_ids": [transaction.source_id],
                "amounts_inr": [_money(transaction.amount_inr)],
                "check": "No PaymentLink was present for this credit transaction.",
                "recommended_follow_up": "Request the related invoice or supporting sales record.",
            })

    by_invoice_number: dict[str, list[Any]] = defaultdict(list)
    for invoice in invoices:
        by_invoice_number[invoice.invoice_no].append(invoice)
    for invoice_no, group in by_invoice_number.items():
        if len(group) > 1:
            anomalies.append({
                "code": "DUPLICATE_INVOICE_IDENTIFIER",
                "severity": "medium",
                "message": f"Invoice identifier {invoice_no} appears more than once. This is a duplicate candidate for review, not proof of misconduct.",
                "record_ids": [item.id for item in group],
                "source_ids": [item.source_id for item in group],
                "amounts_inr": [_money(item.total_inr) for item in group],
                "check": "Grouped invoice records by exact invoice number.",
                "recommended_follow_up": "Compare source documents and retain the supported record.",
            })

    supplier_totals: dict[str, Decimal] = defaultdict(Decimal)
    total_spend = Decimal("0")
    for transaction in transactions:
        if _enum_value(transaction.direction) == "debit" and transaction.counterparty_id:
            supplier_totals[transaction.counterparty_id] += transaction.amount_inr
            total_spend += transaction.amount_inr
    top_supplier_id, top_supplier_amount = (None, Decimal("0"))
    if supplier_totals:
        top_supplier_id, top_supplier_amount = max(supplier_totals.items(), key=lambda item: (item[1], item[0]))
    top_share = (top_supplier_amount / total_spend * 100).quantize(Decimal("0.01")) if total_spend else Decimal("0")
    metrics = {
        "node_count": len(nodes),
        "edge_count": len(edges),
        "supplier_spend_total_inr": _money(total_spend),
        "top_supplier_id": top_supplier_id,
        "top_supplier_spend_inr": _money(top_supplier_amount),
        "top_supplier_share_percent": str(top_share),
        "anomaly_count": len(anomalies),
    }
    return {
        "rule_version": GRAPH_RULE_VERSION,
        "nodes": nodes,
        "edges": edges,
        "anomalies": anomalies,
        "metrics": metrics,
        "provenance": {
            "synthetic": bool(source_by_id) and all(source.synthetic for source in source_by_id.values()),
            "business_id": business.id,
            "source_ids": sorted(source_by_id),
            "data_scope": "business-scoped records only",
            "networkx": nx.__version__,
            "rule_version": GRAPH_RULE_VERSION,
        },
    }
