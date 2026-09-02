# BidVerify AI — Frontend Application

Next.js 16 (App Router + Turbopack) web client for **BidVerify AI — AI-Powered Integrated Bid Compliance Verification Platform for GeM Procurement**.

---

## Tender Management Module (Part 2C)

The Procurement Officer interface at `/procurement/tenders` includes complete end-to-end tender lifecycle operations:

1. **Tender List (`/procurement/tenders`)**:
   * Telemetry cards: Total Listed, Active Drafts, Open for Bidding, Archived.
   * Search input with debounced query execution against the FastAPI backend.
   * Status filter (`DRAFT`, `PUBLISHED`, `OPEN`, `CLOSED`, `UNDER_EVALUATION`, `AWARDED`, `ARCHIVED`).
   * "Show Archived" toggle to query soft-deleted records.
   * Full server-side pagination with record count.
   * Soft-delete archive modal with confirmation safeguards.

2. **Create Tender (`/procurement/tenders/new`)**:
   * Organized 3-section input: Basic Information, Departmental/Financial Details, and Milestones.
   * Form validation with timeline checks and currency valuation constraints.
   * Duplicate tender number handling (409 Conflict alert).

3. **Tender Details (`/procurement/tenders/[id]`)**:
   * Detailed overview, formatted currency values (INR `₹`), scheduled timeline status, owning organization metadata, and dynamic requirements preview.

4. **Edit Tender (`/procurement/tenders/[id]/edit`)**:
   * Pre-populated form for updating active `DRAFT` opportunities.

---

## Route Directory & Access Control

| Route | Purpose | Role Guard |
| :--- | :--- | :--- |
| `/login` | Authentication Portal | Public |
| `/signup` | User & Organization Registration | Public |
| `/bidder/*` | Bidder Portal (Submissions, Clarifications) | `BIDDER` |
| `/procurement/tenders` | Tender Management List | `PROCUREMENT_OFFICER` |
| `/procurement/tenders/new` | Create Tender Form | `PROCUREMENT_OFFICER` |
| `/procurement/tenders/[id]` | View Tender Details | `PROCUREMENT_OFFICER` |
| `/procurement/tenders/[id]/edit` | Edit Tender Form | `PROCUREMENT_OFFICER` |
| `/admin/*` | System Administration & Integrations | `ADMIN` |

---

## Build & Validation

```bash
# Clean production build with Turbopack & TypeScript verification
npm run build

# Start development server
npm run dev
```
