# CREDWEAVE AI live demo (3–4 minutes)

## Before the room

1. Install the backend and frontend dependencies before the event. [Setup instructions](../README.md#clean-install-and-configuration)
2. Start the jury demo from the repository root:

   ```bash
   ./scripts/run-jury-demo.sh
   ```

3. When the server is ready, open <http://127.0.0.1:8080/demo>. The local demo starts with both synthetic cases and their Credit Passports ready.
4. Check both passports and return to Overview. Keep the terminal open during the presentation. Stopping the launcher clears the demo session.
5. Use **Active business** in the header to switch cases during the comparison. The sidebar moves through stages for the current business.

All figures below were checked against the fixed seed and its API responses. Amounts may change if the fixture or calculation rules change.

## Timed walk-through

| Time | Clicks and talk track |
|---|---|
| **0:00–0:25** | **Overview.** “Many small businesses have fragmented records rather than a conventional credit file. CREDWEAVE organizes the available evidence for a human lender; it does not make an approval decision.” Point out the synthetic-data banner and rules-only status. |
| **0:25–0:50** | Click **Business A — stronger evidence**. Both synthetic profiles state a monthly sales claim of **₹1,00,000** in Evidence DNA. Tell judges that the same **₹2,00,000** principal will be used later as a comparison scenario, not as an independently stored application request. |
| **0:50–1:25** | On **Evidence DNA**, compare Business A and B with the **Active business** selector. Both show **100/100 completeness**; consistency differs: A is **90**, B is **43**. The eligible reconciliation counts are 6/6 for A and 3/7 for B. Expand a `CROSS_SOURCE_MATCH` finding and show the record IDs, amounts, sources, and the explicit caveat that alignment is consistency, not authentication. Point to the monthly claim trail; Business A’s observed September credits total ₹1,25,000 because of the planted duplicate-candidate records. |
| **1:25–2:00** | Open **Trust Graph** for Business A. Click **SYNTHETIC - Synthetic Grain Supplier**; the details panel lists its related transaction records with dates, amounts, and source IDs. Then switch to Business B and show the unmatched invoice/payment findings (8 graph findings in this seed). Return to Business A Evidence DNA to show `DUPLICATE_RECORD_CANDIDATE`. Describe each as a review prompt, not fraud. |
| **2:00–2:25** | Open **Financial Health** for both businesses. Compare the six observed months and monthly obligations: A **₹8,500**, B **₹16,500**. The synthetic calculation reports six positive net-cash-flow months for each. Explain that cash-flow indicators and evidence consistency are different dimensions; neither is a default probability or accounting profit. |
| **2:25–3:00** | Open **CashFlow Twin** for Business A. Click **Sales decline**: the minimum modeled net cash is **₹34,800** with the default ₹0 EMI. Click **Combined crisis**; it uses −20% inflows, +15% outflows, a 45-day delay, and two weaker months. Enter **₹18,336** as the selected EMI (the 12-month option shown next); the minimum becomes **−₹66,636** and **₹1,56,800** of modeled receipts fall beyond the six-month horizon. Emphasize timing assumptions and that this is not a forecast. |
| **3:00–3:25** | Open **Loan Options** for Business A. Set/confirm principal **₹2,00,000**, annual interest **18%**, fee **₹0**, and compare 6/12/18/24 months. The API returns monthly EMIs **₹35,105.04 / ₹18,336.00 / ₹12,761.16 / ₹9,984.82**. Longer tenure lowers EMI but raises total interest; every option is illustrative and requires review. |
| **3:25–4:00** | Open the prepared **Credit Passport**. Show its source inventory, snapshot ID/date, uncertainty and limitations, then point out **Prepared for Human Lender Review**. Open **Reviewer Desk** to show the manual checklist and permitted review statuses. No status is an automated approval or denial. |

## Verified demo facts

- Fixed profile names: Business A - Sunrise Foods; Business B - Riverbend Repairs.
- Both evidence endpoints report the same synthetic claim: `100000` INR monthly revenue.
- Completeness is 100 for both; consistency is 90 for A and 43 for B.
- Business A financial summary: ₹6,13,000 inflows, ₹2,28,000 outflows, ₹3,85,000 net cash flow over the observed window; monthly obligations ₹8,500.
- Business B financial summary: ₹5,71,000 inflows, ₹2,28,000 outflows, ₹3,43,000 net cash flow over the observed window; monthly obligations ₹16,500.
- Business B graph: 8 unmatched invoice/payment findings. These are source gaps in this fixture, not evidence of wrongdoing.
- EMI and stress figures above are asserted by the seeded API regression test.

The totals are transaction-derived synthetic outputs; they must not be narrated as verified sales or profit. The profile-level revenue claim is not the same measure as monthly operating cash inflows.
