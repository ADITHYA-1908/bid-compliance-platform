# BidVerify AI — Backend Service

Backend API for **BidVerify AI — AI-Powered Integrated Bid Compliance Verification Platform for GeM Procurement**.

## Overview
Built with **FastAPI**, **SQLAlchemy 2.x**, **Alembic**, **psycopg3**, **bcrypt**, **PyJWT**, and **PostgreSQL** (hosted via **Supabase**).

---

## Document Processing & Structured Entity Extraction (Part 4E)

All document processing and structured extraction endpoints are served under `/api/v1/bidder`:

| Method | Endpoint | Description | Role Policy |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/bidder/bids/{bid_id}/documents/{doc_id}/process` | Queue & execute document processing pipeline | `BIDDER` |
| `POST` | `/api/v1/bidder/bids/{bid_id}/documents/{doc_id}/retry` | Retry processing for `FAILED` or `NEEDS_REVIEW` documents | `BIDDER` |
| `GET` | `/api/v1/bidder/bids/{bid_id}/documents/{doc_id}/extracted-text` | Get extracted text, page count, and classification telemetry | `BIDDER` |
| `GET` | `/api/v1/bidder/bids/{bid_id}/documents/{doc_id}/classification` | Get deterministic document classification & explainability | `BIDDER` |
| `GET` | `/api/v1/bidder/bids/{bid_id}/documents/{doc_id}/extracted-data` | Get normalized structured entity fields, confidence, and page provenance | `BIDDER` |

### Part 4E Features & Extraction Capabilities:
1. **Deterministic-First Extraction**: Regex, label-based proximity scanning, and document-specific parsers extract high-signal entities without external LLM dependencies.
2. **Supported Document Classes & Fields**:
   - **`GST_CERTIFICATE`**: `gstin`, `legal_name`, `trade_name`, `constitution_of_business`, `registration_date`, `principal_place_of_business`, `state`, `status_text`.
   - **`PAN`**: `pan_number`, `name`, `father_name`, `date_of_birth`.
   - **`UDYAM_CERTIFICATE`**: `udyam_registration_number`, `enterprise_name`, `enterprise_classification` (MICRO/SMALL/MEDIUM), `major_activity` (MANUFACTURING/SERVICES/TRADING), `registration_date`, `official_address`.
   - **`OEM_AUTHORIZATION`**: `oem_name`, `authorized_entity`, `reference_number`, `product_or_scope`, `authorization_date`, `valid_until`, `signatory_name`.
   - **`TURNOVER_CERTIFICATE`**: `organization_name`, `financial_years`, `annual_turnover_values` (FY $\to$ numeric amount), `average_annual_turnover`, `certificate_date`, `chartered_accountant_name`, `membership_number`, `udin`.
   - **`FINANCIAL_STATEMENT`**: `financial_year`, `total_revenue`, `profit_before_tax`, `profit_after_tax`, `total_assets`, `auditor_name`.
   - **`EXPERIENCE_CERTIFICATE`**: `organization_name`, `client_name`, `project_name`, `work_order_number`, `start_date`, `completion_date`, `contract_value`.
   - **`LOCAL_CONTENT_DECLARATION`**: `local_content_percentage` (numeric e.g. 65.0), `supplier_class` (Class-I / Class-II), `product_name`, `declaration_date`, `certifying_authority`.
   - **`BLACKLIST_DECLARATION`**: `organization_name`, `blacklisted_status_claim` (boolean claim `false`), `debarred_status_claim`, `declaration_date`, `authorized_signatory`.
   - **`TECHNICAL_DOCUMENT` / `COMMERCIAL_DOCUMENT`**: `quoted_amount`, `currency`, `tax_percentage`, `model_number`, `manufacturer`, `product_name`.
3. **Normalization Engines**:
   - **Indian Currency & Amounts**: Normalizes `5 Crore` $\to$ `50000000.0`, `5.26 Crores` $\to$ `52600000.0`, `45 Lakhs` $\to$ `4500000.0`, `Rs. 85,00,000` $\to$ `8500000.0`.
   - **Dates**: Normalizes `DD/MM/YYYY`, `DD-MM-YYYY`, `DD Month YYYY` to standard ISO `YYYY-MM-DD`.
4. **Field-Level Confidence & Evidence Provenance**: Each field stores `value`, `confidence` ($0.0 - 1.0$), concise `evidence` string, and 1-indexed `page` provenance.
5. **Conflict & Discrepancy Detection**: Multiple conflicting identifiers (e.g. distinct GSTINs or PANs) trigger `requires_review = true` and `NEEDS_REVIEW` processing status.
6. **Graceful Partial Extraction**: Missing optional fields do not crash the pipeline.

> [!NOTE]
> **Important Disclaimer**: Extracted fields represent information read from uploaded documents. They are not yet externally verified against government databases or considered compliant. Part 5 will implement government API verification.

---

## Bid Creation & Tender Participation (Part 3C)

All bidder bid endpoints are served under `/api/v1/bidder` with strict role-based access and tenant isolation:

| Method | Endpoint | Description | Role Policy |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/bidder/tenders/{tender_id}/bids` | Create a new `DRAFT` bid record for an `OPEN` tender | `BIDDER` (100% complete profile required) |
| `GET` | `/api/v1/bidder/tenders/{tender_id}/bid` | Check if authenticated bidder already has a bid for a tender | `BIDDER` |
| `GET` | `/api/v1/bidder/bids` | List bids belonging exclusively to the authenticated bidder's organization | `BIDDER` (cross-tenant isolated) |
| `GET` | `/api/v1/bidder/bids/{bid_id}` | Retrieve full details for draft bid workspace | `BIDDER` (owner org only, 404 on others) |
| `PATCH` | `/api/v1/bidder/bids/{bid_id}` | Update commercial quote, currency, technical notes, and remarks | `BIDDER` (only `DRAFT` bids editable) |

### Part 3C Core Rules & Safeguards:
1. **One Active Bid per Tender**: Enforced via DB unique constraint `uq_bids_tender_organization` (`tender_id`, `bidder_organization_id`) and service-level checks returning `409 Conflict`.
2. **Tender Status Rule**: Only tenders in `OPEN` status allow bid creation. `DRAFT`, `PUBLISHED`, `CLOSED`, `AWARDED`, `ARCHIVED` reject creation with clean 400 validation.
3. **Server-Side Deadline Enforcement**: Current server time in UTC must be $\le$ `submission_end_date`.
4. **Bidder Profile Readiness**: Evaluates 9 mandatory statutory fields (`calculate_profile_completion`). 100% completion is strictly required before participation.
5. **Deterministic Bid Numbers**: Unique sequence identifier generated on backend in `BID-YYYY-XXXXXX` format.
6. **Cross-Tenant Isolation**: Bidders cannot read, modify, or probe other organizations' bids (`404 Not Found` returned on unauthorized IDs).

---

## Tender Requirements & Dynamic Rules (Part 2D)


Endpoints served under `/api/v1/tenders/{tender_id}/requirements`:

| Method | Endpoint | Description | Role Policy |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/tenders/{id}/requirements` | List all dynamic requirements ordered by `display_order` | Authenticated |
| `POST` | `/api/v1/tenders/{id}/requirements` | Attach dynamic requirement rule to `DRAFT` tender | `PROCUREMENT_OFFICER` (owner org) |
| `GET` | `/api/v1/tenders/{id}/requirements/{req_id}` | Get specific requirement rule | Authenticated |
| `PATCH` | `/api/v1/tenders/{id}/requirements/{req_id}` | Update criteria, expected value, weight, or display order | `PROCUREMENT_OFFICER` (owner org) |
| `DELETE` | `/api/v1/tenders/{id}/requirements/{req_id}` | Soft-deactivate requirement (`is_active=false`) | `PROCUREMENT_OFFICER` (owner org) |

---

## Tender Management APIs (Part 2B)

All tender endpoints are served under `/api/v1/tenders` with strict organization-level access isolation:

| Method | Endpoint | Description | Role Policy |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/tenders` | Create new tender in `DRAFT` status (auto-binds organization & creator profile) | `PROCUREMENT_OFFICER` |
| `GET` | `/api/v1/tenders` | List tenders with pagination (`page`, `page_size`), search, status filter, and archive toggle | Authenticated (scoped by role/org) |
| `GET` | `/api/v1/tenders/{id}` | Get full tender details with dynamic requirements | Authenticated (scoped by org) |
| `PATCH` | `/api/v1/tenders/{id}` | Partially update `DRAFT` tender details | `PROCUREMENT_OFFICER` (owner org) |
| `DELETE` | `/api/v1/tenders/{id}` | Soft-delete / archive tender (`is_active=false`, `status='ARCHIVED'`) | `PROCUREMENT_OFFICER` (owner org) |

---

## Database Architecture & Models

```text
organizations
   │
   └── tenders
          │
          └── tender_requirements (Dynamic eligibility & compliance criteria rules)

profiles
   │
   └── created tenders
```

---

## Scoring & Risk Assessment Engines (Part 7)

### Part 7A — Scoring Foundation & Weighting Architecture
- Weighted rule contributions with customizable policies (`REVIEW_UNRESOLVED`, `REVIEW_PARTIAL_CREDIT`).
- Snapshot persistence in `bid_score_snapshots` with versioning and full audit trail.

### Part 7B — Category-wise Compliance Scoring
- 8 canonical procurement categories (`STATUTORY`, `FINANCIAL`, `EXPERIENCE`, `TECHNICAL`, `OEM`, `LOCAL_CONTENT`, `BIS`, `INTEGRITY`).
- Exact weighted formula: $\text{Category Score} = \frac{\sum \text{Earned Weight}}{\sum \text{Eligible Weight}} \times 100$.

### Part 7C — Deterministic Risk Assessment Engine
- Pure mathematical multi-signal base risk evaluation (0–100 scale, higher is riskier).
- Development Risk Model v1 weights:
  - Compliance Deficit: 40.0 pts
  - Failure Rate: 20.0 pts
  - Review Uncertainty Rate: 15.0 pts
  - Pending Rate: 10.0 pts
  - Mandatory Failure Rate: 10.0 pts
  - Integrity & Identity Finding Rate: 5.0 pts
- Risk Level Thresholds: `LOW` $[0, 25)$, `MEDIUM` $[25, 50)$, `HIGH` $[50, 75)$, `CRITICAL` $[75, 100]$.
- Snapshot persistence in `bid_risk_snapshots` with versioning, feature extraction, and explainable audit contributions.

### Part 7D — Critical Overrides & Risk Adjustment Logic
- Pure deterministic post-processing adjustments and minimum risk floors applied on top of Part 7C base risk.
- Preserves Base Risk Score and Base Risk Level without mutation.
- Configured Minimum Risk Floors:
  - Active Blacklisting Failure: Floor 90.00 / `CRITICAL`
  - Active Debarment Failure: Floor 90.00 / `CRITICAL`
  - Multiple Critical Failures ($\ge 2$): Floor 80.00 / `CRITICAL`
  - Single Critical Requirement Failure: Floor 70.00 / `HIGH`
  - Strong Structural Identity Mismatch (PAN/GST): Floor 75.00 / `CRITICAL`
  - Unresolved Critical Review: Floor 50.00 / `HIGH` (provisional escalation)
- Strict Risk Adjustment Rules: Minimum floors never reduce an already higher risk score (`max(score, floor)`).
- Snapshot persistence: `bid_risk_snapshots` records `base_risk_score`, `base_risk_level`, `adjusted_risk_score`, `adjusted_risk_level`, `override_applied`, `override_count`, `override_formula_version`, and itemized `applied_overrides` JSONB.

### Part 7E — RAG + AI Recommendation & Evidence-Based Explanation
- Grounded Retrieval-Augmented Generation (RAG) assistant for authorized Procurement Officers.
- **Vector Storage**: `pgvector` extension in PostgreSQL with HNSW cosine distance indexing (`ix_rag_chunks_embedding_hnsw`).
- **Multi-Source Knowledge Chunks**: Indexes Tender Requirements, Bid Documents, Structured Extractions, Verifications, Compliance Results, Score Snapshots, and Risk Snapshots.
- **Provider Abstraction**: Multi-provider embedding & LLM architecture (`openai`, `gemini`, deterministic `local_fallback`).
- **Security Isolation & Defense**:
  - Strict SQL-level tenant and bid isolation (`tender_id`, `bid_id`, `organization_id`).
  - Untrusted passive evidence boundaries preventing prompt injection from uploaded files.
  - Mock source transparency tags for simulated registries.
- **Deterministic Recommendation Guardrails**:
  - Recommendations: `PROCEED`, `PROCEED_WITH_REVIEW`, `REVIEW_REQUIRED`, `DO_NOT_PROCEED_WITHOUT_REVIEW`, `INSUFFICIENT_EVIDENCE`.
  - Enforces automatic recommendation downgrade to `DO_NOT_PROCEED_WITHOUT_REVIEW` if adjusted risk is `CRITICAL` or critical failures exist.
  - Grounded Citation Validator strips unretrieved / hallucinated citations.
- **Staleness Tracking**: Flags recommendations as `is_stale=True` when upstream compliance, scoring, or risk snapshots change.
- **Procurement Officer Q&A**: Scoped vector search and grounded factual answers to natural language bid inquiries.

---

## Running Verification Tests

```powershell
# Part 7F Master Unified Bid Evaluation Integration Suite
python scripts/test_part7f_unified_evaluation.py

# Part 7E Master RAG + AI Recommendation QA Suite
python scripts/test_part7e_rag_ai_engine.py

# Part 7D Master Critical Overrides & Risk Adjustment Suite
python scripts/test_part7d_override_engine.py

# Part 7C Master Deterministic Risk Assessment Engine Suite
python scripts/test_part7c_risk_engine.py

# Part 7B Master Category Compliance Scoring Suite
python scripts/test_part7b_category_scoring.py

# Part 7A Master Scoring Foundation Suite
python scripts/test_part7a_scoring_foundation.py

# Part 6F Master Compliance Integration Suite
python scripts/test_part6f_master_compliance_qa.py

# Part 5F Master Verification Engine Suite
python scripts/test_part5f_master_verification_qa.py

# Part 4F Master Integration Suite
python scripts/test_part4f_master_integration_qa.py

# Part 2F Full Module Verification Suite
python scripts/test_part2f_full_verification.py
```

