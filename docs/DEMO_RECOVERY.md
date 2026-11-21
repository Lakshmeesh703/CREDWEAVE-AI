# Demo recovery and offline fallback

## Jury demo recovery

The jury launcher hosts the application and API at <http://127.0.0.1:8080/demo>. It uses a fresh synthetic database on each run and can work offline once dependencies are installed.

1. If the page is unavailable, check the launch terminal for build or startup output. Wait for Uvicorn to report that it is running, then reload the page.
2. Check <http://127.0.0.1:8080/api/health> for `status: "ok"` and `synthetic_demo: true`.
3. If the prepared cases are missing or you need a fresh run, stop the launcher and run `./scripts/run-jury-demo.sh` again. Restarting clears changes made in the current demo session.

## Supabase development setup

If the separate development servers cannot reach Supabase, use the jury launcher to present the same synthetic cases locally. For development troubleshooting, verify the configured database target and check <http://localhost:8000/api/health> before reloading the frontend.

## One presentation page fails

- Return to Overview and verify API health first.
- Use the Overview shortcuts to reopen the business from the current API response; do not manually type or guess business IDs.
- If a Passport returns “Create an assessment before generating a credit passport,” open that business’s Risk Insights page and create a fresh assessment snapshot.
- If graph rendering is unavailable, use the graph findings text and source-linked Evidence DNA findings. Describe only what is visible and never call a finding fraud.
