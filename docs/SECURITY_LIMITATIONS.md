# CredWeave portal security and deployment

The signed-in portal uses Supabase Auth for identity. FastAPI sends access tokens to the configured Supabase project for verification and reads the role from its own database. Public registration creates a Business Owner; the first Admin is provisioned with a PostgreSQL-backed operator command. Admins manage account roles without access to financial records.

## Controls in the portal

- Session tokens use HTTP-only, strict SameSite cookies. Enable secure cookies and HTTPS outside local development. Cookie-authenticated writes check the request origin against the configured allowlist.
- Owners can access only their own businesses. Lenders need a per-business grant from the owner and an active Lender role. Review entries are linked to the authenticated lender and the Passport reviewed. Revoking the grant or removing the Lender role blocks subsequent access.
- PostgreSQL table access is denied to browser-facing roles. Startup enables RLS and revokes direct access for `PUBLIC`, `anon`, `authenticated`, and `service_role` when present. FastAPI uses a trusted database credential and enforces per-business rules itself. Keep that credential server-side.
- Original uploads are parsed during the request and are never served through a public file URL. Successful imports persist normalized rows, source names, and SHA-256 hashes. Use masked identifiers and avoid placing personal data in filenames. API responses are marked `no-store`.
- The synthetic demo uses a dedicated loopback launcher and a fresh temporary database. Generated records do not participate in signed-in portal queries. Previously seeded, ownerless rows remain private to the database operator.

## Deployment work before use with sensitive data

The repository supplies a working portal and a local jury demo. A deployment handling sensitive data still needs environment-specific verification and operational controls. Configure HTTPS, exact allowed origins, request and rate limits at the edge, verified email delivery, database backups and migration procedures, and monitoring that excludes credentials and record contents. Review data-retention and deletion requirements for your organization. Revocation applies to future access, and recipients may retain copies already exported.

Credit calculations use deterministic rules and illustrative scenarios. Lender decisions remain human.
