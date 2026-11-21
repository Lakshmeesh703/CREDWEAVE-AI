# CREDWEAVE AI

CredWeave brings small-business financial records together for human lender review. Owners upload evidence, examine reconciliation and cash flow, compare scenarios and loan terms, and generate a source-linked Credit Passport. Lenders review cases shared with them by the owner.

## Start the portal

Install Python 3.11+, Node.js 20+, and npm. From the repository root:

```bash
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt
npm --prefix frontend ci
```

Create a local `.env` from [the example](.env.example) if it does not already exist. If you have one, add the `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, and `AUTH_COOKIE_SECURE` settings while retaining the existing database configuration. Keep `.env` out of version control.

- Configure a dedicated Supabase project with email/password sign-up. Set the Auth **Site URL** to your portal origin. With **Confirm email** enabled, registration waits for Supabase to confirm the email before the user signs in. Configure email delivery for this flow. A local no-email environment can use the provider’s auto-confirm setting, in which case Supabase issues the session and the email address is unverified by delivery. [Supabase Auth settings](https://supabase.com/docs/guides/auth/general-configuration)
- Set `SUPABASE_URL` and its publishable key. `DATABASE_URL` must use the application database credentials for a dedicated PostgreSQL database and a role that owns the application tables. The API applies compatibility changes and protects the tables at startup. Back up an existing database before migrating it.
- After changing `.env`, stop the running backend before launching it again. The launcher reuses a healthy backend, so its environment only changes when that process restarts. Use the publishable key from the project's **Connect** dialog. [Find Supabase API keys](https://supabase.com/docs/guides/getting-started/api-keys)
- For local HTTP use `AUTH_COOKIE_SECURE=0`. For a hosted setup use HTTPS, secure cookies, and an exact `CORS_ORIGINS` allowlist. Serve the frontend and API on the same site so strict cookies are sent. A same-origin reverse proxy can use `VITE_API_BASE_URL=` when building the UI and route `/api/*` to FastAPI. Configure the web server to serve the SPA for frontend routes.

```bash
./scripts/run-project.sh
```

Open <http://localhost:5173> and register an account. Registration signs you in immediately. Use `localhost` consistently for the portal and API in local development. The developer API is at <http://localhost:8000/docs>.

Port 5173 opens the sign-in portal. The jury launcher on port 8080 opens the synthetic dashboard. If the portal launcher reports an older server on its ports, stop it from the terminal where it was started and rerun the launcher.

### Deploy the portal on Render

Use one Python Web Service with **Root Directory** blank. The build creates the React portal and the start command serves it at the same origin as the API so the browser sends the portal's session cookies.

**Build Command**

```bash
pip install -r backend/requirements.txt && npm --prefix frontend ci --include=dev && VITE_API_BASE_URL='' npm --prefix frontend run build && test -f frontend/dist/index.html
```

**Start Command**

```bash
uvicorn app.portal:app --app-dir backend --host 0.0.0.0 --port "$PORT"
```

Keep the database and Supabase settings on the Web Service. Set `AUTH_COOKIE_SECURE=1` and set `CORS_ORIGINS` to the service's exact HTTPS origin without a trailing slash. Use `/api/health` for the Render health check. After redeploying from the updated branch, open the service URL for the portal and `/docs` for the API reference.

On Render, the `app.main:app` entry point also serves the built portal once the build command above has run. The explicit `app.portal:app` entry point works on other hosts too.

### Accounts and verification flow

Login shows **Business Owner**, **Lender**, and **Admin**. Register offers **Business Owner** and **Lender**. Lender registration opens a pending lender workspace with an account ID for Admin approval. An existing account that registered under the wrong option can use **Request lender access** if it owns no businesses. A project operator provisions Admin accounts.

Sign in using the option for the role assigned to your account. Pending applicants use **Lender**. New and reset passwords require at least 15 characters and a maximum of 72 UTF-8 bytes. Previously set passwords are still accepted by the sign-in form.

1. **Business Owner** is assigned on the first successful sign-in. Open **Businesses**, register a profile, and grant upload consent. The business is private by default. The account ID is shown on the workspace page.
2. **Admin** is bootstrapped once from a dedicated account that has signed in and registered no businesses. From the repository root:

   ```bash
   cd backend
   set -a
   source ../.env
   set +a
   .venv/bin/python -m app.bootstrap_admin <supabase-user-uuid>
   ```

   Replace the placeholder with the account ID. Sign in as the administrator and assign **Lender** to a dedicated account after it has signed in once. Account management excludes business records and financial evidence.
3. **Lender** signs back in after assignment and sends their account ID to the owner. The owner uses **Share with a lender** within a specific business. While the grant is active, the lender can inspect that business's current and future evidence and Passports and record a manual review. The owner can revoke access from the same screen. Revocation blocks future API access. It cannot retrieve copies already exported.

### Password recovery

Business Owners and Lenders choose a private security question during registration and receive a one-time recovery code. Existing accounts can set up or replace recovery from **Password recovery** in the portal, using their current password. To reset a forgotten password, use **Forgot password?** from the appropriate sign-in page. Enter the saved code to see the question, then provide the answer and a new password. Save the replacement code after a successful reset.

The backend needs a server-only `SUPABASE_SECRET_KEY` for recovery. Add it to the local `.env` and restart the API. The app keeps a salted hash of the security answer and a hash of the recovery code. Admin accounts use the project's administrator-managed recovery process. [Supabase API keys](https://supabase.com/docs/guides/getting-started/api-keys)

### Uploads and analysis

| Upload | Required columns |
| --- | --- |
| Bank and UPI transactions, CSV | `external_ref,transaction_date,amount_inr,direction,payment_channel,description,currency` |
| Invoices and supplier bills, CSV | `invoice_no,issued_at,due_at,total_inr,direction,status` |
| Supplier directory, CSV | `counterparty_name,identifier_masked` |
| Payment obligations, CSV or JSON | `monthly_payment_inr,description` |

Both transaction and invoice formats support `counterparty_name,counterparty_type,identifier_masked`. Use the same masked identifier across sources to link records. Supplier invoices use `payable`; customer invoices use `receivable`. Transactions use `credit` or `debit`, INR, and a channel of `bank_transfer`, `upi`, or `cash`. Dates use `YYYY-MM-DD`. Invoices accept `open`, `paid`, `partial`, or `overdue`. Supply UTF-8 files up to 2 MB. The API validates imports transactionally. The portal shows successful sources, normalized records, and validation errors for rejected files.

Once transactions are imported, open **Evidence DNA**, **Trust Graph**, **Financial Health**, **CashFlow Twin**, and **Loan Options**. Create a dated assessment from **Risk Insights** to generate a **Credit Passport**. Create a fresh snapshot after adding evidence if you want the Passport to reflect it. The assessment includes illustrative loan and scenario assumptions. Live scenario and loan calculations read uploaded business transactions from the server.

The reviewer can record **Pending**, **Needs more information**, or **Reviewed** against a specific Passport. The rules and scenarios support a human lender. [Risk model limitations](docs/RISK_MODEL_LIMITATIONS.md)

### Data protection

Supabase verifies the user session. Application roles, ownership, and lender-specific consent are enforced in FastAPI. PostgreSQL RLS is enabled with direct table access revoked from Supabase's browser roles. The trusted FastAPI connection is the data gateway. Files are parsed into normalized records and have no public storage URLs. Existing rows with no owner are preserved and stay outside the signed-in portal until an operator verifies ownership and migrates them.

See the [deployment and security limitations](docs/SECURITY_LIMITATIONS.md) before exposing the portal publicly or uploading sensitive records.

## Verified Evidence Gateway

The gateway adds record provenance, CSV review flags, and append-only verification history. See the [gateway guide](docs/VERIFIED_EVIDENCE_GATEWAY.md) for the PostgreSQL migration, input formats, and status meanings.

## Synthetic demo

```bash
./scripts/run-jury-demo.sh
```

Open <http://127.0.0.1:8080/demo>. The launcher builds and serves the demo and API from a loopback server with its own temporary SQLite database. Both sample businesses and their prepared Credit Passports are marked **SYNTHETIC DEMO**. This works offline after dependency installation. Stopping the launcher clears its database. The regular portal's `/demo` page links to the isolated launcher. If port 8080 is occupied, set `CREDWEAVE_JURY_PORT` when launching and `VITE_DEMO_URL` for the portal link.

[Four-minute jury walkthrough](docs/DEMO_SCRIPT.md) · [Judge one-pager](docs/JUDGE_ONE_PAGER.md) · [Judge Q&A](docs/JUDGE_QA.md) · [Recovery guide](docs/DEMO_RECOVERY.md)

## Verification

```bash
(cd backend && .venv/bin/python -m pytest)
npm --prefix frontend test
npm --prefix frontend run lint
npm --prefix frontend run build
```

Portal tests use isolated SQLite and a mocked Supabase Auth response. They cover session and origin checks, ownership, CSV-driven analysis, named lender consent and revocation, human review, and role management. Live email confirmation requires a configured Supabase project with working mail delivery. The [UI modernization and QA guide](docs/UI_MODERNIZATION.md) lists the role routes, API contracts, live checks, and product limits.

[Architecture](docs/ARCHITECTURE.md) · [Data dictionary](docs/DATA_DICTIONARY.md) · [Evaluation](docs/EVALUATION.md)
