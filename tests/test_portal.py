from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app import auth
from app.main import app


@pytest.fixture
def portal(monkeypatch):
    def verify(path, *, token=None, payload=None):
        if path == "user":
            if token not in users:
                raise HTTPException(401, "Credentials or session could not be verified.")
            return {"id": token, "email": "owner@example.test", "email_confirmed_at": "2026-01-01", "user_metadata": {"role": "admin"}}
        if path == "settings":
            return {"mailer_autoconfirm": True}
        if path == "signup" or path.startswith("token?"):
            return {"access_token": users[0], "refresh_token": "refresh", "expires_in": 3600, "user": {"id": users[0]}}
        return {}

    users = [str(uuid4()) for _ in range(3)]
    monkeypatch.setattr(auth, "supabase", verify)
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "0")
    with TestClient(app) as client:
        yield client, users


def headers(user):
    return {"Authorization": f"Bearer {user}"}


def business_payload():
    return {"name": "Harbour Makers", "sector": "Manufacturing", "city": "Pune",
            "operating_months": 18, "consent_status": "pending", "source_upload_consent": True}


def test_registration_and_cookie_origin_controls(portal):
    client, users = portal
    credentials = {"email": "owner@example.test", "password": "example-password"}
    origin = {"Origin": "http://localhost:5173"}
    signup = client.post("/api/auth/register", json=credentials, headers=origin)
    assert signup.status_code == 200 and signup.json() == {"signed_in": True}
    assert "HttpOnly" in signup.headers["set-cookie"]
    assert client.get("/api/me").json()["role"] == "owner"
    login = client.post("/api/auth/login", json=credentials, headers=origin)
    assert login.status_code == 200
    assert "HttpOnly" in login.headers["set-cookie"]
    assert "access_token" not in login.json()
    assert client.get("/api/me").json()["role"] == "owner"
    assert client.post("/api/businesses", json=business_payload()).status_code == 403
    assert client.post("/api/businesses", json=business_payload(), headers=origin).status_code == 201
    assert client.post("/api/auth/logout", headers=origin).status_code == 200
    assert client.get("/api/me").status_code == 401
    assert client.get("/api/me", headers=headers(users[1])).json()["role"] == "owner"


def test_registration_preserves_email_confirmation_and_pending_lender_role(portal, monkeypatch):
    from app.db.session import SessionLocal
    from app.models.entities import PortalAccount

    client, users = portal
    calls = []
    identities = [{"provider": "email"}]

    def provider(path, **kwargs):
        calls.append(path)
        if path == "settings":
            return {"mailer_autoconfirm": False}
        if path == "signup":
            return {"id": users[0] if identities else users[1], "identities": identities}
        raise AssertionError(path)

    monkeypatch.setattr(auth, "supabase", provider)
    origin = {"Origin": "http://localhost:5173"}
    payload = {"email": "lender@example.test", "password": "example-password", "account_type": "lender"}
    for existing in (False, True):
        if existing:
            identities.clear()
        response = client.post("/api/auth/register", headers=origin, json=payload)
        assert response.status_code == 200
        assert response.json() == {"signed_in": False, "confirmation_required": True}
        assert "set-cookie" not in response.headers
    assert calls == ["settings", "signup", "settings", "signup"]
    with SessionLocal() as db:
        assert db.get(PortalAccount, users[0]).role == "lender_pending"
        assert db.get(PortalAccount, users[1]) is None


def test_owner_isolation_and_demo_disabled(portal):
    client, users = portal
    a, b = map(headers, users[:2])
    assert client.get("/api/businesses").status_code == 401
    assert client.get("/api/businesses", headers=headers("forged")).status_code == 401
    create = client.post("/api/businesses", headers=a, json=business_payload())
    assert create.status_code == 201, create.text
    ident = create.json()["id"]
    base = f"/api/businesses/{ident}"
    assert client.get("/api/businesses", headers=b).json() == []
    for path in ("", "/sources", "/records?kind=transactions", "/records-summary", "/evidence-dna",
                 "/evidence-findings", "/trust-graph", "/graph-findings", "/financial-summary",
                 "/assessments/latest", "/credit-passport", "/review-workspace"):
        assert client.get(base + path, headers=b).status_code == 404, path
    assert client.put(base, headers=b, json=business_payload()).status_code == 404
    assert client.put(base, headers=a, json={**business_payload(), "city": "Mumbai"}).json()["city"] == "Mumbai"
    assert client.post("/api/demo/load", headers=a).status_code == 403


def test_uploaded_evidence_drives_the_entire_owner_pipeline(portal):
    client, users = portal
    h = headers(users[0])
    ident = client.post("/api/businesses", headers=h, json=business_payload()).json()["id"]
    base = f"/api/businesses/{ident}"
    assert client.post(base + "/assess", headers=h).status_code == 422
    assert client.post(base + "/stress-tests", headers=h, json={}).status_code == 422
    assert client.get(base + "/records?kind=transactions", headers=h).json()["items"] == []

    transactions = (
        "external_ref,transaction_date,amount_inr,direction,payment_channel,description,currency,"
        "counterparty_name,counterparty_type,identifier_masked\n"
        "R-77,2025-09-11,21300,credit,upi,Customer receipt,INR,Vale Works,customer,V-XX\n"
        "P-79,2025-09-12,3100,debit,upi,Supplier payment,INR,Maple Supplies,supplier,M-XX\n"
    )
    invoices = (
        "invoice_no,issued_at,due_at,total_inr,direction,status,counterparty_name,counterparty_type,identifier_masked\n"
        "I-77,2025-09-11,2025-10-11,21300,receivable,paid,Vale Works,customer,V-XX\n"
        "I-79,2025-09-12,2025-10-12,3100,payable,paid,Maple Supplies,,M-XX\n"
    )
    suppliers = "counterparty_name,identifier_masked\nMaple Supplies,M-XX\nNew Supplier,N-XX\n"
    for kind, content in (("transactions", transactions), ("invoices", invoices), ("suppliers", suppliers)):
        upload = client.post(base + f"/imports/{kind}", headers=h,
                             files={"file": (f"{kind}.csv", content, "text/csv")})
        assert upload.status_code == 200, upload.text
        assert upload.json()["accepted_rows"] == 2
    invalid = client.post(base + "/imports/transactions", headers=h, files={
        "file": ("invalid.csv", transactions.replace("21300", "NaN"), "text/csv"),
    })
    assert invalid.status_code == 422
    sources = client.get(base + "/sources", headers=h).json()
    assert {item["kind"] for item in sources} == {"upi", "invoice", "supplier"}
    assert all(item["parsing_status"] == "imported" and not item["synthetic"] for item in sources)
    assert len(client.get(base + "/records?kind=transactions", headers=h).json()["items"]) == 2
    evidence = client.get(base + "/evidence-dna", headers=h).json()
    assert evidence["claim_to_evidence"]["reported_amount_inr"] is None
    assert not evidence["provenance"]["synthetic"]
    assert evidence["evidence_consistency"]["matched"] == 1
    graph = client.get(base + "/trust-graph", headers=h).json()
    assert "Maple Supplies" in str(graph["nodes"])
    new_supplier = next(node for node in graph["nodes"] if node["label"] == "New Supplier")
    directory = next(item for item in sources if item["kind"] == "supplier")
    assert new_supplier["source_ids"] == [directory["id"]]
    assert any(edge["target"] == new_supplier["id"] and edge["type"] == "LISTED_SUPPLIER" for edge in graph["edges"])
    financial = client.get(base + "/financial-summary", headers=h).json()
    assert financial["metrics"]["net_operating_cash_flow"]["value"] == "18200.00"
    stress = client.post(base + "/stress-tests", headers=h, json={"duration_months": 1}).json()
    assert stress["metrics"]["minimum_net_cash_after_emi_inr"] == "18200.00"
    assert client.post(base + "/stress-tests", headers=h, json={
        "base_monthly": [{"inflows_inr": "99999", "outflows_inr": "0"}],
    }).status_code == 422
    terms = {"principal_inr": "12000", "annual_interest_rate_pct": 0, "tenure_months": [12]}
    options = client.post(base + "/loan-options", headers=h, json={**terms, "scenario_preset": "normal"}).json()
    assert options["options"][0]["emi_inr"] == "1000.00"
    assert options["options"][0]["minimum_post_emi_cash_inr"] == "17200.00"
    assert client.post(base + "/loan-options", headers=h, json={
        **terms, "selected_scenario": [{"inflows_inr": "99999", "outflows_inr": "0"}],
    }).status_code == 422
    snapshot = client.post(base + "/assess", headers=h)
    assert snapshot.status_code == 201, snapshot.text
    passport = client.get(base + "/credit-passport", headers=h).json()
    assert passport["assessment_id"] == snapshot.json()["assessment_id"]
    assert passport["snapshot"]["financial_summary"]["metrics"]["net_operating_cash_flow"]["value"] == "18200.00"


def test_named_lenders_can_review_only_while_the_owner_grant_is_active(portal):
    from app.db.session import SessionLocal
    from app.models.entities import PortalAccount, Review
    from sqlalchemy import select

    client, users = portal
    owner_id, lender_id, other_id = users
    owner_headers, lender_headers, other_headers = map(headers, users)
    for candidate in (lender_id, other_id):
        assert client.get("/api/me", headers=headers(candidate)).status_code == 200
        with SessionLocal.begin() as db:
            db.get(PortalAccount, candidate).role = "lender"
    ident = client.post("/api/businesses", headers=owner_headers, json=business_payload()).json()["id"]
    base = f"/api/businesses/{ident}"
    assert client.get("/api/businesses", headers=lender_headers).json() == []
    assert client.get(base, headers=lender_headers).status_code == 404
    assert client.post("/api/businesses", headers=lender_headers, json=business_payload()).status_code == 403
    grant = f"{base}/shares/{lender_id}"
    assert client.put(grant, headers=lender_headers).status_code == 404
    assert client.put(grant, headers=owner_headers).status_code == 200
    assert client.put(grant, headers=owner_headers).status_code == 200
    assert client.get("/api/businesses", headers=lender_headers).json()[0]["id"] == ident
    assert client.get("/api/businesses", headers=other_headers).json() == []
    assert client.get(base + "/financial-summary", headers=other_headers).status_code == 404
    assert client.put(base, headers=lender_headers, json=business_payload()).status_code == 403
    assert client.post(base + "/assess", headers=lender_headers).status_code == 403

    upload = "external_ref,transaction_date,amount_inr,direction,payment_channel,description,currency\nA,2025-10-01,21300,credit,upi,Receipt,INR\n"
    assert client.post(base + "/imports/transactions", headers=owner_headers,
                       files={"file": ("review.csv", upload, "text/csv")}).status_code == 200
    assessment_id = client.post(base + "/assess", headers=owner_headers).json()["assessment_id"]
    assert client.get(base + "/credit-passport", headers=lender_headers).status_code == 200
    entry = {"assessment_id": assessment_id, "reviewer_name_or_alias": "Impersonated reviewer",
             "reason": "Request a recent statement.", "status": "needs_more_information"}
    assert client.post(base + "/reviews", headers=owner_headers, json=entry).status_code == 403
    assert client.post(base + "/reviews", headers=other_headers, json=entry).status_code == 404
    assert client.post(base + "/reviews", headers=lender_headers,
                       json={**entry, "status": "approved"}).status_code == 422
    assert client.post(base + "/reviews", headers=lender_headers,
                       json={**entry, "assessment_id": "stale"}).status_code == 409
    recorded = client.post(base + "/reviews", headers=lender_headers, json=entry)
    assert recorded.status_code == 201, recorded.text
    assert recorded.json()["reviewer_name_or_alias"] == f"Lender {lender_id[:8]}"
    with SessionLocal() as db:
        assert db.scalar(select(Review).where(Review.id == recorded.json()["id"])).reviewer_account_id == lender_id
    assert client.get(base + "/review-workspace", headers=owner_headers).json()["reviews"]
    assert client.delete(grant, headers=owner_headers).status_code == 200
    assert client.get("/api/businesses", headers=lender_headers).json() == []
    assert client.get(base + "/credit-passport", headers=lender_headers).status_code == 404
    assert client.post(base + "/reviews", headers=lender_headers, json=entry).status_code == 404
    assert client.get(base + "/credit-passport", headers=owner_headers).status_code == 200


def test_admin_manages_lender_roles_without_access_to_evidence(portal):
    from app.db.session import SessionLocal
    from app.models.entities import PortalAccount

    client, users = portal
    staff_id, lender_id, owner_id = users
    staff, lender, owner = map(headers, users)
    for h in (staff, lender, owner):
        assert client.get("/api/me", headers=h).status_code == 200
    with SessionLocal.begin() as db:
        db.get(PortalAccount, staff_id).role = "admin"

    route = "/api/admin/accounts"
    assert client.get(route, headers=owner).status_code == 403
    assert len(client.get(route + "?limit=1", headers=staff).json()["items"]) == 1
    assert client.put(f"{route}/{lender_id}/role", headers=staff, json={"role": "admin"}).status_code == 422
    assert client.put(f"{route}/{staff_id}/role", headers=staff, json={"role": "lender"}).status_code == 403
    assert client.put(f"{route}/{lender_id}/role", headers=staff, json={"role": "lender"}).status_code == 200
    assert client.get("/api/me", headers=lender).json()["role"] == "lender"
    ident = client.post("/api/businesses", headers=owner, json=business_payload()).json()["id"]
    base = f"/api/businesses/{ident}"
    assert client.put(f"{route}/{owner_id}/role", headers=staff, json={"role": "lender"}).status_code == 409
    assert client.get(base + "/sources", headers=staff).status_code == 404
    assert client.get("/api/businesses", headers=staff).json() == []
    assert client.put(f"{base}/shares/{lender_id}", headers=owner).status_code == 200
    assert client.get(base, headers=lender).status_code == 200
    assert client.put(f"{route}/{lender_id}/role", headers=staff, json={"role": "owner"}).status_code == 200
    assert client.get(f"{base}/shares", headers=owner).json() == []
    assert client.put(f"{route}/{lender_id}/role", headers=staff, json={"role": "lender"}).status_code == 200
    assert client.get(base, headers=lender).status_code == 404


def test_supabase_user_verification_uses_configured_service_and_rejects_invalid_tokens(monkeypatch):
    import httpx

    monkeypatch.setenv("SUPABASE_URL", "https://project.example.test")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "test-publishable-key")
    calls = []

    def mock(method, url, *, headers, json, timeout):
        calls.append((method, url, headers, json))
        return httpx.Response(401, json={"message": "Invalid token"})

    monkeypatch.setattr(auth.httpx, "request", mock)
    with pytest.raises(HTTPException) as exc:
        auth.supabase("user", token="bad-token")
    assert exc.value.status_code == 401
    assert calls == [("GET", "https://project.example.test/auth/v1/user",
                      {"apikey": "test-publishable-key", "Authorization": "Bearer bad-token"}, None)]


def test_api_responses_are_private_and_oversized_uploads_are_rejected(portal):
    client, users = portal
    response = client.get("/api/me", headers=headers(users[0]))
    assert response.headers["cache-control"] == "no-store"
    response = client.post("/api/businesses/unknown/imports/transactions", headers={
        **headers(users[0]), "Content-Length": str(3 * 1024 * 1024),
    }, content=b"")
    assert response.status_code == 413
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize(("status", "code", "message"), [
    (429, "over_email_send_rate_limit", "limited confirmation emails"),
    (429, "over_request_rate_limit", "Too many authentication requests"),
    (403, "email_address_not_authorized", "cannot send confirmation email"),
])
def test_supabase_auth_errors_preserve_safe_guidance_and_retry_after(monkeypatch, status, code, message):
    import httpx

    monkeypatch.setenv("SUPABASE_URL", "https://project.example.test")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "test-publishable-key")
    response = httpx.Response(status, json={"error_code": code}, headers={"Retry-After": "60"})
    monkeypatch.setattr(auth.httpx, "request", lambda *args, **kwargs: response)
    with pytest.raises(HTTPException) as exc:
        auth.supabase("signup", payload={})
    assert exc.value.status_code == status
    assert message in exc.value.detail
    if status == 429:
        assert exc.value.headers == {"Retry-After": "60"}


@pytest.mark.parametrize("role", ["owner", "lender"])
def test_password_reset_requires_code_and_answer_and_rotates_code(portal, monkeypatch, role):
    from app import password_recovery
    from app.db.session import SessionLocal
    from app.models.entities import PasswordRecovery, PortalAccount

    client, users = portal
    origin = {"Origin": "http://localhost:5173"}
    question = "What private hint did I save?"
    answer = "some private phrase"
    signup = client.post("/api/auth/register", headers=origin, json={
        "email": "owner@example.test", "password": "example-password",
        "recovery": {"question": question, "answer": answer},
    })
    assert signup.status_code == 200, signup.text
    code = signup.json()["recovery_code"]
    root = "/api/auth/recovery"
    with SessionLocal.begin() as db:
        db.get(PortalAccount, users[0]).role = role
        record = db.get(PasswordRecovery, users[0])
        assert record.answer_hash != answer and record.code_hash != code
    assert client.post(root + "/question", headers=origin, json={"code": "x" * 32}).status_code == 403
    assert client.post(root + "/question", headers=origin, json={"code": code}).json() == {"question": question}
    calls = []
    monkeypatch.setattr(password_recovery, "update_password", lambda account, password: calls.append((account, password)))
    payload = {"code": code, "answer": answer, "password": "my-new-password"}
    assert client.post(root + "/reset", json=payload).status_code == 403
    assert client.post(root + "/reset", headers=origin, json={**payload, "answer": "wrong answer"}).status_code == 403
    assert calls == []
    result = client.post(root + "/reset", headers=origin, json=payload)
    assert result.status_code == 200, result.text
    assert calls == [(users[0], "my-new-password")]
    assert result.json()["recovery_code"] != code
    assert client.post(root + "/reset", headers=origin, json=payload).status_code == 403

    with SessionLocal.begin() as db:
        db.get(PortalAccount, users[0]).role = "admin"
    replacement = result.json()["recovery_code"]
    assert client.post(root + "/question", headers=origin, json={"code": replacement}).status_code == 403
    assert client.post(root + "/reset", headers=origin, json={**payload, "code": replacement}).status_code == 403
    assert client.post(root + "/setup", headers=origin, json={
        "recovery": {"question": question, "answer": answer}, "password": "my-new-password",
    }).status_code == 403


def test_recovery_setup_and_answer_rate_limit(portal):
    client, users = portal
    h = {**headers(users[0]), "Origin": "http://localhost:5173"}
    root = "/api/auth/recovery"
    result = client.post(root + "/setup", headers=h, json={
        "recovery": {"question": "What is my private hint?", "answer": "correct answer"},
        "password": "current-password",
    })
    assert result.status_code == 200, result.text
    payload = {"code": result.json()["recovery_code"], "answer": "incorrect answer", "password": "new-password-long"}
    for _ in range(4):
        assert client.post(root + "/reset", headers=h, json=payload).status_code == 403
    response = client.post(root + "/reset", headers=h, json=payload)
    assert response.status_code == 429
    assert response.headers["Retry-After"] == "900"
    assert client.post(root + "/reset", headers=h, json={**payload, "answer": "correct answer"}).status_code == 429


def test_supabase_password_update_uses_only_the_server_key(monkeypatch):
    import httpx
    from app import password_recovery

    monkeypatch.setenv("SUPABASE_URL", "https://project.example.test")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "sb_secret_example")
    account_id = str(uuid4())

    def update(url, **kwargs):
        assert url == f"https://project.example.test/auth/v1/admin/users/{account_id}"
        assert kwargs["headers"] == {"apikey": "sb_secret_example"}
        assert kwargs["json"] == {"password": "new-password-long"}
        return httpx.Response(200)

    monkeypatch.setattr(password_recovery.httpx, "put", update)
    password_recovery.update_password(account_id, "new-password-long")


def test_lender_signup_persists_pending_role_until_admin_approves(portal):
    from app.db.session import SessionLocal
    from app.models.entities import PortalAccount

    client, users = portal
    origin = {"Origin": "http://localhost:5173"}
    credentials = {"email": "lender@example.test", "password": "example-password"}
    assert client.post("/api/auth/register", json={**credentials, "account_type": "admin"}, headers=origin).status_code == 422
    response = client.post("/api/auth/register", json={**credentials, "account_type": "lender",
                           "recovery": {"question": "What is my private hint?", "answer": "secret phrase"}}, headers=origin)
    assert response.status_code == 200, response.text
    assert response.json()["recovery_code"]
    assert client.get("/api/me").json()["role"] == "lender_pending"
    assert client.post("/api/businesses", headers=origin, json=business_payload()).status_code == 403
    assert client.get("/api/businesses").json() == []
    assert client.post("/api/auth/logout", headers=origin).status_code == 200
    assert client.post("/api/auth/login", headers=origin, json={**credentials, "role": "lender"}).status_code == 200
    assert client.get("/api/me").json()["role"] == "lender_pending"
    route = f"/api/admin/accounts/{users[0]}/role"
    assert client.put(route, headers=origin, json={"role": "lender"}).status_code == 403

    staff = headers(users[1])
    assert client.get("/api/me", headers=staff).status_code == 200
    with SessionLocal.begin() as db:
        db.get(PortalAccount, users[1]).role = "admin"
    assert client.put(route, headers=staff, json={"role": "lender"}).status_code == 200
    assert client.get("/api/me").json()["role"] == "lender"


def test_existing_empty_owner_account_can_enter_lender_setup(portal):
    client, users = portal
    owner, other = map(headers, users[:2])
    assert client.post("/api/businesses", headers=other, json=business_payload()).status_code == 201
    assert client.post("/api/me/lender-access", headers=other).status_code == 409
    response = client.post("/api/me/lender-access", headers=owner)
    assert response.status_code == 200
    assert response.json()["role"] == "lender_pending"
    assert client.post("/api/businesses", headers=owner, json=business_payload()).status_code == 403


def test_gateway_preserves_provenance_and_audit_history_across_reconciliation(portal):
    from hashlib import sha256
    from app.db.session import SessionLocal
    from app.models.entities import PortalAccount

    client, users = portal
    owner, lender, stranger = map(headers, users)
    business = client.post("/api/businesses", headers=owner, json=business_payload()).json()["id"]
    root = f"/api/businesses/{business}"
    gateway = root + "/verified-evidence"

    assert client.patch(root + "/upload-consent?granted=false", headers=stranger).status_code == 404
    assert client.patch(root + "/upload-consent?granted=false", headers=owner).json()["source_upload_consent"] is False

    csv = (
        "external_ref,transaction_date,amount_inr,direction,payment_channel,description,currency,source_provider,balance_inr\n"
        "TX-1,2025-05-01,1000,credit,upi,Receipt,INR,Claimed institution,1000\n"
        "TX-2,2025-05-02,25,debit,upi,,INR,Claimed institution,500\n"
    ).encode()
    invoice = b"invoice_no,issued_at,due_at,total_inr,direction,status\nINV-1,2025-05-01,2025-05-31,1000,receivable,paid\n"
    bad = csv.replace(b"TX-2", b"TX-1")
    assert client.post(root + "/imports/transactions", headers=owner,
                       files={"file": ("bad.csv", bad, "text/csv")}).status_code == 422
    assert client.get(gateway, headers=owner).json()["items"] == []
    assert client.post(root + "/imports/transactions", headers=owner,
                       files={"file": ("statement.csv", csv, "text/csv")}).status_code == 403
    assert client.patch(root + "/upload-consent?granted=true", headers=owner).json()["source_upload_consent"] is True
    upload = client.post(root + "/imports/transactions", headers=owner,
                         files={"file": ("statement.csv", csv, "text/csv")})
    assert upload.json()["requires_review"] == 1
    assert client.post(root + "/imports/invoices", headers=owner,
                       files={"file": ("invoice.csv", invoice, "text/csv")}).status_code == 200
    contents = client.get(gateway, headers=owner).json()
    assert contents["counts"] == {"UNVERIFIED": 2, "REQUIRES_REVIEW": 1}
    tx = next(record for record in contents["items"] if record["original_source_reference"] == "TX-1")
    assert tx["file_sha256"] == sha256(csv).hexdigest()
    assert tx["source_provider"] == "Claimed institution"
    assert (tx["record_date"], tx["amount_inr"], tx["source_label"]) == ("2025-05-01", "1000.00", "statement.csv")
    filtered = client.get(gateway, headers=owner, params={"search": "statement.csv", "kind": "transaction", "sort": "amount", "limit": 1}).json()
    assert filtered["matching_count"] == 2
    assert filtered["next_offset"] == 1
    assert filtered["items"][0]["record_id"] == tx["record_id"]
    assert client.get(gateway, headers=owner, params={"search": "%"}).json()["matching_count"] == 0
    assert tx["uploaded_at"] and tx["result"]["verified_at"]
    assert tx["source_type"] == "USER_UPLOAD"
    review = client.get(gateway, headers=owner, params={"status": "REQUIRES_REVIEW"}).json()
    assert len(review["items"]) == 1
    assert {item["code"] for item in review["items"][0]["result"]["findings"]} == {
        "MISSING_DESCRIPTION", "RUNNING_BALANCE_MISMATCH",
    }

    assert client.post(root + "/assess", headers=owner).status_code == 201
    assert client.post(gateway + "/reconcile", headers=owner).json()["records_updated"] == 2
    assert client.post(gateway + "/reconcile", headers=owner).json()["records_updated"] == 0
    after = client.get(gateway, headers=owner, params={"status": "PARTIALLY_SUPPORTED"}).json()
    assert after["counts"] == {"PARTIALLY_SUPPORTED": 2, "REQUIRES_REVIEW": 1}
    reviewed_tx = next(row for row in after["items"] if row["record_id"] == tx["record_id"])
    assert reviewed_tx["provenance_id"] == tx["provenance_id"]
    assert reviewed_tx["file_sha256"] == tx["file_sha256"]
    assert reviewed_tx["result"]["supporting_evidence"]
    history_url = gateway + "/" + tx["provenance_id"] + "/history"
    history = client.get(history_url, headers=owner).json()
    assert [item["status"] for item in history["items"]] == ["UNVERIFIED", "PARTIALLY_SUPPORTED"]
    assert client.get(root + "/credit-passport", headers=owner).json()["snapshot"]["evidence_dna"]["gateway_status_counts"] == contents["counts"]
    assert client.post(root + "/assess", headers=owner).status_code == 201
    assert client.get(root + "/credit-passport", headers=owner).json()["snapshot"]["evidence_dna"]["gateway_status_counts"] == after["counts"]

    assert client.get(gateway, headers=stranger).status_code == 404
    assert client.get(history_url, headers=stranger).status_code == 404
    assert client.get("/api/me", headers=lender).status_code == 200
    with SessionLocal.begin() as db:
        db.get(PortalAccount, users[1]).role = "lender"
    assert client.get(gateway, headers=lender).status_code == 404
    assert client.put(f"{root}/shares/{users[1]}", headers=owner).status_code == 200
    assert client.get("/api/lender/queue", headers=owner).status_code == 403
    queue = client.get("/api/lender/queue", headers=lender).json()
    assert len(queue) == 1 and queue[0]["business"]["id"] == business
    assert queue[0]["review_status"] == "awaiting_review"
    assert client.get(history_url, headers=lender).json() == history
    assert client.post(root + "/reviews", headers=lender, json={
        "assessment_id": queue[0]["assessment_id"], "status": "needs_more_information", "reason": "Please supply the missing statement.",
    }).status_code == 201
    assert client.get("/api/lender/queue", headers=lender).json()[0]["review_status"] == "needs_more_information"
    assert client.get(root + "/credit-passport", headers=lender).json()["latest_review"]["status"] == "needs_more_information"
    assert client.get("/api/lender/queue", headers=stranger).status_code == 403
    assert client.post(gateway + "/reconcile", headers=lender).status_code == 403
    assert client.delete(f"{root}/shares/{users[1]}", headers=owner).status_code == 200
    assert client.get(history_url, headers=lender).status_code == 404
    assert client.get("/api/lender/queue", headers=lender).json() == []


@pytest.mark.parametrize(("role", "sign_in_role"), [
    ("owner", "owner"), ("lender", "lender"), ("lender_pending", "lender"), ("admin", "admin"),
])
def test_login_only_sets_cookies_for_the_assigned_role(portal, role, sign_in_role):
    from app.db.session import SessionLocal
    from app.models.entities import PortalAccount

    client, users = portal
    assert client.get("/api/me", headers=headers(users[0])).status_code == 200
    with SessionLocal.begin() as db:
        db.get(PortalAccount, users[0]).role = role

    origin = {"Origin": "http://localhost:5173"}
    credentials = {"email": "owner@example.test", "password": "legacy-pass"}
    for wrong_role in {"admin", "lender", "owner"} - {sign_in_role}:
        denied = client.post("/api/auth/login", headers=origin, json={**credentials, "role": wrong_role})
        assert denied.status_code == 409
        assert "set-cookie" not in denied.headers
        assert client.get("/api/me").status_code == 401

    result = client.post("/api/auth/login", headers=origin, json={**credentials, "role": sign_in_role})
    assert result.status_code == 200
    assert "HttpOnly" in result.headers["set-cookie"]
    assert client.get("/api/me").json()["role"] == role


@pytest.mark.parametrize("password", ["short", " " * 15, "🔒" * 19, "a" * 73])
def test_registration_and_recovery_share_the_password_policy(portal, monkeypatch, password):
    from app import password_recovery

    client, _ = portal
    origin = {"Origin": "http://localhost:5173"}

    def unexpected(*args, **kwargs):
        pytest.fail("The provider must not be called for an invalid new password.")

    monkeypatch.setattr(auth, "supabase", unexpected)
    monkeypatch.setattr(password_recovery, "update_password", unexpected)
    signup = client.post("/api/auth/register", headers=origin,
                         json={"email": "owner@example.test", "password": password})
    reset = client.post("/api/auth/recovery/reset", headers=origin,
                        json={"code": "x" * 32, "answer": "secret phrase", "password": password})
    assert signup.status_code == reset.status_code == 422


@pytest.mark.parametrize("password", ["a  long phrase with  spaces", "🔒" * 18, "x" * 72])
def test_password_policy_allows_passphrases_and_bcrypt_byte_boundary(password):
    auth.check_new_password(password)
