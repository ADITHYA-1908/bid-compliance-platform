# BidVerify AI

**AI-Powered Integrated Bid Compliance Verification Platform for GeM Procurement**

---

## Status: Part 8F COMPLETE — Final Platform Integration, Security, Performance & End-to-End QA
### BIDVERIFY AI PLATFORM STATUS: 100% COMPLETE & PRODUCTION-READY

BidVerify AI automates and streamlines the verification of bid documents, technical compliance, financial credentials, and regulatory requirements for procurement on the Government e-Marketplace (GeM).

### Modules & Completion Status

```text
Next.js 16 Frontend (App Router)
        ↓ (Bearer JWT / Multipart FormData / Type-Safe Client)
Reusable API Client (frontend/src/lib/api.ts)
        ↓ (CORS / HTTP / Pydantic JSON & Streaming)
FastAPI Backend (backend/app)
        ↓ (10 Specialized Evaluators + Cross-Document Consistency Engine + Audit Ledger)
PostgreSQL Database (Supabase) + Private Storage Bucket (bid-documents)
```

| Sub-Module | Title | Status |
| :--- | :--- | :--- |
| **Part 1** | Full Application Foundation (Setup, DB, Auth, RBAC, Layout, Integration) | **Completed** |
| **Part 2A** | Tender Data Model & Database Foundation (`tenders`, `tender_requirements`) | **Completed** |
| **Part 2B** | Tender CRUD Backend APIs & Business Logic | **Completed** |
| **Part 2C** | Procurement Officer Tender Management UI & Workflows | **Completed** |
| **Part 2D** | Requirement Builder & Dynamic Rule Form | **Completed** |
| **Part 2E** | Tender Lifecycle & Status Management (State Machine & Locking) | **Completed** |
| **Part 2F** | Tender Module Final Integration, QA, Bug Fixing & Hardening | **Completed** |
| **Part 3A** | Bidder Profile & Organization Setup (Statutory Identifiers & Completion) | **Completed** |
| **Part 3B** | Bidder Tender Discovery (Search, Filters, Visibility & Detail View) | **Completed** |
| **Part 3C** | Bid Creation & Tender Participation (Draft Workspace & Lifecycle Rules) | **Completed** |
| **Part 3D** | Bid Document Upload (Private Storage, Requirement Mapping, Versioning) | **Completed** |
| **Part 3E** | Bid Review & Final Submission Workflow (Readiness, Declaration, Locking) | **Completed** |
| **Part 3F** | Bidder Module Final Integration, QA, Hardening & Security Testing | **Completed** |
| **Part 4A** | Document Processing Foundation (Storage & Lifecycle Pipeline) | **Completed** |
| **Part 4B** | Digital PDF Text Extraction using PyMuPDF | **Completed** |
| **Part 4C** | OCR & Image Preprocessing using PaddleOCR + OpenCV | **Completed** |
| **Part 4D** | Deterministic Document Classification Engine | **Completed** |
| **Part 4E** | Structured Entity / Field Extraction Engine | **Completed** |
| **Part 4F** | Final Document Processing Integration, Review & QA | **Completed** |
| **Part 5A** | Verification Engine Foundation & Adapter Architecture | **Completed** |
| **Part 5B** | GST, PAN & Udyam Statutory Verification | **Completed** |
| **Part 5C** | MCA, Startup India, NSIC, EPFO & ESIC Verification | **Completed** |
| **Part 5D** | OEM, Local Content, BIS/DPIIT & Supporting Document Verification | **Completed** |
| **Part 5E** | Blacklisting, Debarment & Cross-Document Consistency Checks | **Completed** |
| **Part 5F** | Verification Integration, Evidence, Confidence & Final QA | **Completed** |
| **Part 6A** | Compliance Engine Foundation & Rule Evaluation Architecture | **Completed** |
| **Part 6B** | Statutory & Registration Compliance Rules | **Completed** |
| **Part 6C** | Financial, Experience & Technical Compliance Rules | **Completed** |
| **Part 6D** | OEM, Local Content, BIS & Document Compliance | **Completed** |
| **Part 6E** | Blacklisting, Debarment, Critical Rules & Review Logic | **Completed** |
| **Part 6F** | Final Compliance Integration & QA | **Completed** |
| **Part 7A** | Scoring Engine Foundation & Weighting Architecture | **Completed** |
| **Part 7B** | Category-wise Compliance Scoring | **Completed** |
| **Part 7C** | Deterministic Risk Assessment Engine | **Completed** |
| **Part 7D** | Critical Overrides & Risk Adjustments | **Completed** |
| **Part 7E** | RAG + AI Recommendation & Evidence-Based Explanation | **Completed** |
| **Part 7F** | Unified Bid Evaluation Summary & Regression Testing | **Completed** |
| **Part 8A** | Procurement Evaluation Dashboard Foundation | **Completed** |
| **Part 8B** | Bid Evaluation Matrix & Comparative Scoring | **Completed** |
| **Part 8C** | Human Review & Evidence Inspection | **Completed** |
| **Part 8D** | Final Human Decision Workflow | **Completed** |
| **Part 8E** | Audit Trail, Decision History & Reports | **Completed** |
| **Part 8F** | Final Platform Integration, Security, Performance & End-to-End QA | **Completed** |


---

## Compliance Engine Foundation (Part 6A)

Part 6A introduces the core **Compliance Engine Foundation & Rule Evaluation Architecture**:

> [!NOTE]
> Part 6A evaluates individual tender requirements against verified bidder claims and documents. It does NOT compute overall Compliance Scores (0–100%), overall Risk Levels, or automated qualification decisions (which belong to Part 7 & Part 8).

```text
Tender Requirement (Part 2) + Verified Bidder Evidence (Part 5)
        ↓
Compliance Engine Context
        ↓
Compliance Evaluator Registry
        ↓
Generic & Specialized Rule Evaluators (Decimal Numeric, Date, String, Boolean, Exists)
        ↓
Rule Determinations (PASS / FAIL / REVIEW / NOT_APPLICABLE / PENDING)
        ↓
Evidence-Linked Snapshot & Audit Trail (compliance_results)
```

### Key Capabilities & Architecture:
* **Centralized Statuses**: `PASS`, `FAIL`, `REVIEW`, `NOT_APPLICABLE`, `PENDING`, `BLOCKED`.
* **Centralized Operators**: `EQUALS`, `NOT_EQUALS`, `GREATER_THAN`, `GREATER_THAN_OR_EQUAL`, `LESS_THAN`, `LESS_THAN_OR_EQUAL`, `CONTAINS`, `EXISTS`, `NOT_EXISTS`.
* **Prerequisite Handling**:
  - `VERIFIED`: Evaluated against verified source values.
  - `UNAVAILABLE` or `FAILED`: Returns `REVIEW` with explanatory reason without penalizing bidders for third-party outages.
  - `NEEDS_REVIEW`: Returns `REVIEW` referencing source review flags.
  - `NOT_VERIFIED`: Returns `FAIL` for mandatory credentials.
* **Audit & History**: Versioned evaluation (`evaluation_version`), marking superseded results `is_current = False`.

---

## Statutory & Registration Compliance (Part 6B)

Part 6B implements specialized statutory and registration rule evaluation across all major GeM public procurement domains:

> [!NOTE]
> Part 6B evaluates only statutory and registration-related tender requirements. Financial, technical, OEM, local-content, BIS, blacklisting, and critical-rule evaluation are handled in subsequent Part 6 subparts.

```text
Tender Requirement (GST, PAN, Udyam, MCA, Startup, NSIC, EPFO, ESIC)
        +
Verified Registration Records (Part 5)
        ↓
Statutory Rule Evaluator (StatutoryRuleEvaluator)
        ↓
PASS / FAIL / REVIEW / PENDING / NOT_APPLICABLE
        ↓
Structured Reason & Provenance Evidence
```

### Supported Statutory Domains & Rule Logic:
1. **GST Rules**:
   - `GST_REGISTRATION`: Confirms active GSTIN registration in authoritative source.
   - `GST_STATUS`: Compares verified registry status (e.g. `ACTIVE` vs `CANCELLED`/`SUSPENDED`) against requirement target.
2. **PAN Rules**:
   - `PAN_REQUIRED` / `PAN_VERIFICATION`: Confirms verified PAN cardholder record.
   - Name Mismatch Gate: Automatically places determination in `REVIEW` when cardholder name differs from bidder organization name.
3. **Udyam & MSME Rules**:
   - `UDYAM_REGISTRATION`: Confirms active MSME registration.
   - `MSME_CLASSIFICATION`: Evaluates enterprise category (`MICRO`, `SMALL`, `MEDIUM`) with support for `IN` list matching.
4. **MCA Registration & Company Status**:
   - `MCA_COMPANY_STATUS`: Evaluates company incorporation status (`ACTIVE`, `DORMANT`, `UNDER_LIQUIDATION`, `STRIKE_OFF`).
   - Applicability Engine: Automatically sets `NOT_APPLICABLE` for `PROPRIETORSHIP` / `INDIVIDUAL` bidders when company-specific.
5. **Startup India Recognition**:
   - `STARTUP_INDIA_RECOGNITION`: Evaluates DPIIT recognition status (`RECOGNIZED` vs `REVOKED`/`EXPIRED`).
6. **NSIC Registration & Validity**:
   - `NSIC_VALIDITY`: Compares certificate `valid_until` against tender submission deadline / target milestone date chronologically.
7. **EPFO & ESIC Registration**:
   - `EPFO_REGISTRATION` & `ESIC_REGISTRATION`: Evaluates statutory labor establishment registration and active status.
8. **Prerequisite & Resilience Policy**:
   - `UNAVAILABLE` or `FAILED` source verification generates `REVIEW` without penalizing the bidder with a `FAIL`.
   - Missing required verification generates `PENDING`.
9. **Master QA Coverage**:
   - `test_part6b_statutory_compliance.py`: **100% PASSED**
   - `test_part6a_compliance_engine.py`: **100% PASSED**
   - `test_part5f_master_verification_qa.py`: **44/44 PASSED (100%)**
   - Next.js production build: **32/32 routes compiled (0 errors)**.

---

## Financial, Experience & Technical Compliance (Part 6C)

Part 6C implements specialized financial, past experience, and deterministic technical compliance evaluation:

> [!NOTE]
> Part 6C evaluates financial capabilities, past project experience, and deterministic technical specifications. OEM, local-content, BIS, blacklisting, critical rules, scoring, risk, and final decisions remain outside this subpart.

```text
Tender Requirements (Financial, Experience, Technical)
        +
Verified Records (Part 5) & Structured Extractions (Part 4)
        ↓
Financial / Experience / Technical Evaluators
        ↓
PASS / FAIL / REVIEW / PENDING
        ↓
Structured Reasons & Audit Provenance (compliance_results)
```

### Supported Evaluators & Domain Logic:
1. **Financial Compliance (`FinancialComplianceEvaluator`)**:
   - **Annual Turnover**: Normalizes Indian currency units (`Crore`, `Lakh`, `Million`, commas, `₹`) into deterministic `Decimal` representations and evaluates against requirement thresholds.
   - **Multi-Year Average Annual Turnover**: Computes exact `Decimal` averages across required financial years (e.g. 3 years). Missing financial years return `REVIEW` without silent/arbitrary averaging.
   - **Profitability Rules**: Evaluates `Profit After Tax > 0` / positive net profit requirements. Missing profit data returns `REVIEW` (no guessing from turnover).
   - **Document Presence**: Handles `FINANCIAL_STATEMENT_REQUIRED` as document-presence check.
   - **Conflict & Confidence Resilience**: Flags conflicting turnover values across documents or low-confidence extractions as `REVIEW`.
2. **Experience & Past Performance (`ExperienceComplianceEvaluator`)**:
   - **Years of Experience**: Calculates exact duration from start and completion dates, merging overlapping date intervals to eliminate double counting.
   - **Completed Projects Count**: Evaluates counts of projects with verified completion proof (`status == 'COMPLETED'` or completion date).
   - **Single Project Value Threshold**: Evaluates whether at least one completed project meets the minimum single contract value (`max(contract_value) >= threshold`).
   - **Total Project Value Summation**: Computes cumulative completed contract value sum using `Decimal`.
   - **Similar Projects Deterministic Matching**: Deterministically matches project scope and category without LLM hallucinations.
3. **Technical & Parametric Compliance (`TechnicalComplianceEvaluator`)**:
   - **Technical Document Presence**: Confirms presence of data sheets, brochures, or product catalogs.
   - **Model Number Matching**: Performs exact normalized matching (e.g. `X-100` matches `X100`).
   - **Product / Manufacturer Matching**: Normalized case-insensitive string matching.
   - **Technical Specifications**: Evaluates structured parametric fields (e.g. throughput capacity, voltage, dimensions) against numeric and string operator rules.
   - **Unstructured / Missing Parameters**: Returns explainable `REVIEW` without arbitrary semantic guessing.
4. **Master QA Coverage**:
   - `test_part6c_financial_experience_technical.py`: **34/34 PASSED (100%)**
   - `test_part6b_statutory_compliance.py`: **100% PASSED**
   - `test_part6a_compliance_engine.py`: **100% PASSED**
   - `test_part5f_master_verification_qa.py`: **44/44 PASSED (100%)**
   - Next.js production build: **32/32 routes compiled (0 errors)**.

---

## OEM, Local Content, BIS & Document Compliance (Part 6D)

Part 6D implements specialized compliance rule evaluation for OEM Authorizations, Make-in-India (MII) local content, BIS certifications, and generic supporting documents against verified Part 5 records:

> [!NOTE]
> Part 6D evaluates OEM, local-content, BIS and supporting-document tender requirements. Blacklisting, critical mandatory-rule handling, overall scoring, risk and final decisions are implemented later.

```text
Tender Requirements (OEM, Local Content, BIS, Documents)
        +
Verified Records (Part 5) & Active Document Extractions (Part 4)
        ↓
Part 6D Compliance Evaluators
        ↓
PASS / FAIL / REVIEW / PENDING / NOT_APPLICABLE
        ↓
Structured Reasons & Audit Provenance (compliance_results)
```

### Supported Evaluators & Domain Logic:
1. **OEM Authorization Compliance (`OEMComplianceEvaluator`)**:
   - **Presence & Authenticity**: Verifies active OEM authorization against manufacturer records.
   - **Authorized Entity Matching**: Verifies whether the authorization explicitly names and authorizes the bidding organization (`MATCH` $\rightarrow$ `PASS`, `MISMATCH` $\rightarrow$ `FAIL`).
   - **Authorization Validity**: Validates `valid_until >= tender_submission_deadline`. Missing validity date generates explainable `REVIEW`.
   - **Product / Scope Match**: Verifies covered equipment model/scope against tender scope (`PARTIAL_MATCH` $\rightarrow$ `REVIEW`).
2. **Local Content / Make in India Compliance (`LocalContentComplianceEvaluator`)**:
   - **Percentage Threshold**: Evaluates verified local content percentage against minimum requirement using exact `Decimal` arithmetic (e.g. $55\% \ge 50\% \rightarrow \text{PASS}$, $45\% < 50\% \rightarrow \text{FAIL}$).
   - **Supplier Classification**: Evaluates Make-in-India supplier class (`CLASS_I`, `CLASS_II`, `NON_LOCAL`), supporting multiple allowed classes (`IN`).
   - **Percentage Range Validation**: Flags impossible percentages ($<0\%$ or $>100\%$) as `REVIEW`.
   - **Declaration Presence**: Verifies presence of Make-in-India declaration document.
3. **BIS Certification Compliance (`BISComplianceEvaluator`)**:
   - **Registration Presence**: Evaluates presence of active BIS CRS/License number.
   - **Registry Status**: Validates status (`VALID` $\rightarrow$ `PASS`, `EXPIRED`/`SUSPENDED`/`CANCELLED` $\rightarrow$ `FAIL`).
   - **Indian Standard Conformance**: Evaluates exact normalized match of Indian Standard (e.g. `IS 13252`).
   - **Certificate Validity**: Validates `valid_until >= tender_milestone_date`.
   - **Manufacturer / Licensee Match**: Normalizes and checks licensee name match.
4. **Supporting Document Compliance (`SupportingDocumentEvaluator`)**:
   - **Mandatory vs Optional**: Missing mandatory document $\rightarrow$ `FAIL`, missing optional document $\rightarrow$ `NOT_APPLICABLE`.
   - **Processing Integrity**: Failed document processing $\rightarrow$ `REVIEW` (human review required).
   - **Internal Evidence Linkage**: Links structural verification for non-registry affidavits.
5. **Master QA Coverage**:
   - `test_part6d_oem_local_content_bis_documents.py`: **35/35 PASSED (100%)**
   - `test_part6c_financial_experience_technical.py`: **34/34 PASSED (100%)**
   - `test_part6b_statutory_compliance.py`: **100% PASSED**
   - `test_part6a_compliance_engine.py`: **100% PASSED**
   - `test_part5f_master_verification_qa.py`: **44/44 PASSED (100%)**
   - Next.js production build: **32/32 routes compiled (0 errors)**.

---

## Blacklisting, Debarment, Critical Rules & Review Logic (Part 6E)

Part 6E implements specialized exclusion, integrity, and cross-document consistency rule evaluation with critical failure detection and structured human review queue generation:

> [!NOTE]
> Part 6E identifies critical and mandatory compliance failures and review items, but does not make the final qualification/disqualification decision or compute composite risk scores (which belong to Part 7 & Part 8).

```text
Tender Requirements + Part 5E Verification Records (Blacklist, Debarment, Consistency)
        ↓
Integrity & Consistency Compliance Evaluator (IntegrityComplianceEvaluator)
        ↓
PASS / FAIL / REVIEW / PENDING / NOT_APPLICABLE
        ↓
Critical Failure Flags (`critical_failure = True`) + Human Review Queue (`review_items`)
```

### Supported Evaluators & Domain Logic:
1. **Blacklisting Compliance Rules**:
   - **Authoritative Clearance**: Evaluates registry status (`CLEAR` $\rightarrow$ `PASS`, `BLACKLISTED` $\rightarrow$ `FAIL`).
   - **Declaration Conflict Detection**: Accurately flags conflicts where self-declaration claimed clearance but external registry reported active blacklisting (`declaration_conflict = True`).
   - **Uncertain / Phonetic Matches**: Partial entity-name matches without definitive identifier match evaluate to `REVIEW` (`VERIFICATION_UNCERTAIN`), avoiding premature disqualification.
   - **Outage Resilience**: Source unavailability returns `REVIEW` without penalizing the bidder.
2. **Debarment Compliance & Chronological Window**:
   - **Active Debarment**: Debarment orders covering the tender submission deadline evaluate to `FAIL`.
   - **Expired Debarment**: Previous debarments where `effective_until < tender_milestone_date` evaluate to `PASS`.
   - **Future Debarment**: Orders taking effect after the tender milestone evaluate to `PASS` for historical submissions.
3. **Cross-Document Identity Consistency**:
   - **PAN ↔ GSTIN Matching**: Strict check comparing extracted PAN against embedded PAN in verified GSTIN (`MATCH` $\rightarrow$ `PASS`, `MISMATCH` $\rightarrow$ `FAIL`).
   - **Legal Organization Name Matching**: Name discrepancies across certificates evaluate to `REVIEW` for partial matches and `FAIL`/`REVIEW` based on rule criticality.
   - **Registered Address Consistency**: Address variations evaluate conservatively to `REVIEW` rather than premature failure.
4. **Critical vs Mandatory Separation**:
   - `is_mandatory`: Indicates standard requirement where satisfaction is expected.
   - `is_critical`: Indicates high-severity statutory/integrity rule where failure triggers `critical_failure = True`.
   - Counts in summary distinguish `mandatory_failures` and `critical_failures`.
5. **Review Summary Queue**:
   - Aggregates all `REVIEW` determinations into a structured bid-level review list with `review_type`, human-readable `reason`, and `evidence`.
6. **Master QA Coverage**:
   - `test_part6e_blacklisting_critical_rules.py`: **35/35 PASSED (100%)**
   - `test_part6d_oem_local_content_bis_documents.py`: **35/35 PASSED (100%)**
   - `test_part6c_financial_experience_technical.py`: **34/34 PASSED (100%)**
   - `test_part6b_statutory_compliance.py`: **100% PASSED**
   - `test_part6a_compliance_engine.py`: **100% PASSED**
   - `test_part5f_master_verification_qa.py`: **44/44 PASSED (100%)**
   - Next.js production build: **32/32 routes compiled (0 errors)**.

---

## Complete Verification Architecture (Part 5)

Part 5 provides a unified, auditable, multi-domain claim verification framework:

> [!NOTE]
> Part 5 verifies bidder claims, source data authenticity, and cross-document identity consistency using configured verification sources. It does NOT determine tender compliance (Part 6) or final bidder risk scores (Part 7).

```text
Structured Extracted Claims
        ↓
Verification Engine
        ↓
┌────────────────────────────────────────────────────────────────────────┐
│ Statutory: GST, PAN, Udyam, MCA                                       │
│ Registrations: Startup India, NSIC, EPFO, ESIC                        │
│ Technical Evidence: OEM Authorization, Local Content (MII), BIS, DPIIT│
│ Internal Evidence: Supporting Documents & Financial Affidavits        │
│ Integrity Checks: Blacklisting Registry, Debarment Registry           │
│ Coherence: Cross-Document & Cross-Source Consistency Engine           │
└────────────────────────────────────────────────────────────────────────┘
        ↓
Standardized Verification Results (Evidence + Confidence + Source + Review Flags)
        ↓
Ready for Part 6 — Automated Compliance Engine
```

### Key Verification Engine Guarantees:
* **Registry Status Separation**: Verified registry state (e.g. `CANCELLED`, `EXPIRED`, `BLACKLISTED`, `DEBARRED`) is stored independently from execution `verification_status` (`VERIFIED`, `NEEDS_REVIEW`, `NOT_VERIFIED`, `UNAVAILABLE`, `FAILED`).
* **Deterministic Confidence**: Bounded 0.0 to 1.0 based strictly on match rules and corroboration.
* **Separation of Claimed vs. Verified**: Claimed payload and verified payload are preserved without mutation.
* **Audit & History**: Incremental retry progression (`attempt_number`), superseding replaced documents while preserving past verification history.
* **Multi-Tenant Security**: Tenant ownership strictly isolated; unauthorized inspection returns HTTP 404.
* **Master QA Coverage**:
  - `test_part5f_master_verification_qa.py`: **44/44 PASSED (100%)**
  - `test_part5e_blacklisting_consistency.py`: **27/27 PASSED (100%)**
  - `test_part5d_oem_local_content_bis_supporting.py`: **38/38 PASSED (100%)**
  - Next.js production build: **32/32 routes compiled with 0 errors**.

---

## Blacklisting, Debarment & Cross-Document Consistency (Part 5E)

Part 5E introduces risk-integrity screening and cross-source coherence checking:

> [!NOTE]
> Part 5E identifies verification findings and consistency mismatches. It does not itself determine tender compliance (Part 6) or final bidder risk scoring (Part 7).

### Key Capabilities & Engine:

* **Mock Blacklisting Adapter (`MockBlacklistingAdapter`)**:
  - Matches organizations across `PAN` $\rightarrow$ `GSTIN` $\rightarrow$ `CIN` $\rightarrow$ `UDYAM` $\rightarrow$ `Legal Name`.
  - Preserves registry status: `CLEAR`, `BLACKLISTED`, `EXPIRED`.
  - Detects self-declaration conflict (Declared Clean vs. Blacklisted $\rightarrow$ `NEEDS_REVIEW`).
* **Mock Debarment Adapter (`MockDebarmentAdapter`)**:
  - Evaluates active and expired debarment windows against mock registries.
* **Cross-Document Consistency Engine (`cross_document_consistency_service.py`)**:
  - **PAN $\leftrightarrow$ GSTIN**: Compares standalone PAN with embedded 10-character PAN in GSTIN. Mismatches trigger `NEEDS_REVIEW` (`HIGH_ATTENTION`).
  - **Organization Name**: Normalized pairwise token comparison across Profile, GST, PAN, Udyam, MCA, EPFO, ESIC, OEM docs.
  - **CIN / LLPIN**: Exact normalized comparison between Profile, MCA, and documents.
  - **Udyam Number**: Exact alignment across Profile, Certificate, and MSME verification.
  - **Registered State & Address**: State equality and token-level address validation.
  - **Organization Entity Type**: Canonical normalization (`PRIVATE_LIMITED`, `PUBLIC_LIMITED`, `LLP`, `PARTNERSHIP`, `PROPRIETORSHIP`, `TRUST`, etc.).
* **Provenance & Review Summary**:
  - Each finding clearly retains provenance (`source_a`, `source_b`, `value_a`, `value_b`, `match_status`, `severity_hint`, `requires_review`).
* **Automated QA Coverage**:
  - 27 automated tests in `backend/scripts/test_part5e_blacklisting_consistency.py` (100% pass rate).

---

## OEM, Local Content, BIS/DPIIT & Supporting Document Verification (Part 5D)

Part 5D extends the verification engine to support technical, manufacturing, and supporting document evidence validation:

> [!NOTE]
> Part 5D uses mock, sandbox, and internal evidence verification. It does not claim official government verification unless a real authorized source is configured.

### Key Capabilities & Adapters:

* **Mock OEM Authorization Adapter (`MockOEMAuthorizationAdapter`)**:
  - Validates OEM reference numbers, OEM manufacturer identity, authorized grantee bidder, product scope, and authorization validity window (`valid_from` to `valid_until`).
  - Preserves `authorization_status: "VALID"` or `"EXPIRED"`.
* **Mock Local Content Adapter (`MockLocalContentAdapter`)**:
  - Numeric percentage parsing and comparison (`normalize_percentage`, `compare_percentages`).
  - Supplier class normalization (`Class-I Local Supplier` $\rightarrow$ `CLASS_I`, `CLASS_II`, `NON_LOCAL`).
  - Matches declarant entity and product name against mock MII declarations registry.
* **Mock BIS Adapter (`MockBISAdapter`)**:
  - Validates BIS registration numbers (`R-XXXXXXXX`), standard numbers (`IS 13252`), and manufacturer names.
  - Preserves `registry_status: "VALID"` or `"EXPIRED"`.
* **Mock DPIIT Adapter (`MockDPIITAdapter`)**:
  - Validates Make-in-India public procurement policy orders without duplicating Part 5C Startup India recognition.
* **Internal Supporting Document Adapter (`InternalSupportingDocumentAdapter`)**:
  - Evaluates internal structural checklist (reference number, issuer name, document date, signatory, substantive financial/scope data) for CA certificates, experience letters, and technical declarations with source type `INTERNAL`.
* **Strict Verification vs. Compliance Boundary**:
  - Verification authenticates claims and evidence.
  - Tender threshold evaluation (e.g. minimum 50% local content, expired OEM validity rules) is strictly evaluated in Part 6.
* **Automated QA Coverage**:
  - 38 automated tests in `backend/scripts/test_part5d_oem_local_content_bis_supporting.py` (100% pass rate).

---

## MCA, Startup India, NSIC, EPFO & ESIC Verification (Part 5C)

Part 5C expands the statutory verification engine with 5 new deterministic domain adapters using synthetic mock registry fixtures:

> [!NOTE]
> Part 5C uses deterministic mock/sandbox sources for development and testing. It does not claim official government API connectivity.

### Key Capabilities & Adapters:

* **Mock MCA Adapter (`MockMCAVerificationAdapter`)**:
  - Validates 21-character Corporate Identification Number (CIN) and LLPIN.
  - Extracts structural metadata: listing status (`Listed`/`Unlisted`), state, year of incorporation, and company type code (`PTC` $\rightarrow$ Private Limited, `PLC` $\rightarrow$ Public Limited).
  - Matches corporate name against mock MCA registry.
  - Preserves corporate status (`ACTIVE`, `DORMANT`, `STRIKE_OFF`).
* **Mock Startup India Adapter (`MockStartupIndiaVerificationAdapter`)**:
  - Validates DPIIT recognition numbers (`DIPP...`).
  - Matches entity name and stores `startup_status` (`RECOGNIZED`, `EXPIRED`, `REVOKED`) and `sector`.
* **Mock NSIC Adapter (`MockNSICVerificationAdapter`)**:
  - Validates NSIC Single Point Registration Scheme numbers.
  - Matches enterprise name and preserves certificate validity window (`valid_from` to `valid_until`) and enterprise `category`.
* **Mock EPFO Adapter (`MockEPFOVerificationAdapter`)**:
  - Validates 15-character alphanumeric EPFO establishment codes.
  - Matches establishment name and preserves `coverage_status` (`ACTIVE`, `INACTIVE`) and regional office state.
* **Mock ESIC Adapter (`MockESICVerificationAdapter`)**:
  - Validates 17-digit numeric ESIC employer registration codes.
  - Matches employer name and preserves `registration_status` (`ACTIVE`, `INACTIVE`) and regional office.
* **Strict Verification vs. Compliance Separation**:
  - Statutory claims are verified strictly for authenticity and registry matches.
  - Tender PASS/FAIL, qualification rules, and scoring remain isolated in Part 6.
* **Automated QA Coverage**:
  - 53 automated tests in `backend/scripts/test_part5c_mca_startup_nsic_epfo_esic_verification.py` (100% pass rate).
* **Automated QA Coverage**:
  - 39 automated tests in `backend/scripts/test_part5b_gst_pan_udyam_verification.py` (100% pass rate).

---

## Bidder Module Final Integration, QA & Hardening (Part 3F)

Part 3F provides comprehensive end-to-end integration, security validation, edge case hardening, and full regression verification across the entire GeM Bidder Platform:

### Key Hardening & Security Policies:

* **End-to-End Regression Test Suite**: Automated 10-phase verification in `backend/scripts/test_part3f_bidder_e2e_regression.py` covering all 64 critical acceptance criteria with 100% pass rate.
* **Authentication & Role-Based Access Control**: 401 Unauthenticated & 403 Forbidden enforcement on bidder mutations and cross-role requests.
* **Statutory Profile Completion Gate**: Profile score calculated across 9 statutory fields (`trade_name`, `organization_type`, `business_category`, `pan_number`, `gstin`, `registered_address`, `city`, `state`, `pincode`). Bids cannot be created or submitted if completeness $< 100\%$.
* **Tender Discovery Safe Projections**: Bidders only see `OPEN` tenders with sanitized public metadata. Private procurement officer IDs and internal audit notes are strictly excluded.
* **Bid Creation & Lifecycle Rules**: 
  - Unique `BID-YYYY-XXXXXX` generated per proposal.
  - Active duplicate bid prevention per organization + tender (`409 Conflict`).
  - Closed/Draft/Archived tender bid prevention (`400 Bad Request`).
  - Server-side deadline expiration gate (`400 Bad Request`).
* **Cross-Tenant Isolation**: Multi-tenant data partition ensuring Bidder A cannot view, mutate, upload to, or submit Bidder B's bid proposal (strict `404 Not Found`).
* **Document Security & Storage**:
  - Private Supabase Storage bucket (`bid-documents`) with short-lived HMAC signed URLs.
  - File extension blacklist blocking executable scripts (`.exe`, `.bat`, `.cmd`, `.ps1`, `.sh`).
  - Strict 25MB file size limit.
  - Single-active requirement mapping with deterministic auto-replacement of superseded versions.
* **Readiness & Immutability**:
  - 5-point readiness checklist (Profile 100%, Proposal Details, Mandatory Documents, Tender OPEN, Server Deadline).
  - Explicit statutory legal declaration required before submission.
  - Atomic transition to `SUBMITTED` with `SUB-YYYY-XXXXXX` reference and tamper-evident receipt.
  - Post-submission permanent lock rejecting proposal edits (`PATCH`) and document mutations (`POST/PUT/DELETE`).
* **Procurement Officer & Tender Management Regression**: All Part 2 tender creation, requirement builder, and lifecycle state transitions (`DRAFT` $\rightarrow$ `PUBLISHED` $\rightarrow$ `OPEN`) remain fully operational.

---

## Bid Review & Final Submission Workflow (Part 3E)

Part 3E implements the pre-submission readiness validation, legal declaration binding, atomic `DRAFT` $\rightarrow$ `SUBMITTED` state transition, post-submission mutation locking, and on-screen tamper-evident submission receipting.

### Key Capabilities & Workflow Rules:

* **Granular Submission Readiness Gate**: Dynamically evaluates 5 mandatory criteria before allowing final submission:
  1. *Bidder Profile Completeness*: 100% statutory profile fields (9 statutory items verified).
  2. *Proposal Details*: Commercial `quoted_amount` ($>0$) and `technical_summary` present.
  3. *Mandatory Compliance Documents*: All active mandatory requirements have active linked documents.
  4. *Tender Status*: Tender must remain in `OPEN` status.
  5. *Submission Deadline*: Server UTC clock must not have passed `submission_end_date`.
* **Statutory Declaration Enforcement**: Bidders must explicitly accept the legal declaration before submission is enabled.
* **Atomic State Transition**: `DRAFT` $\rightarrow$ `SUBMITTED`, persisting `submitted_at`, `submitted_by_profile_id`, `declaration_accepted=True`, `declaration_accepted_at`, and generating unique `submission_reference` (e.g. `SUB-YYYY-XXXXXX`).
* **Post-Submission Mutation Locks**: All detail edits (`PATCH /bids/{id}`) and document operations (`POST/PUT/DELETE /bids/{id}/documents`) on submitted bids are strictly rejected with `409 Conflict` / `400 Bad Request`.
* **Tamper-Evident Submission Receipt**: Real-time on-screen receipt with submission reference, timestamp, signatory name, email, and lock badge.
* **Strict Tenant Isolation**: Cross-bidder readiness inspection and submission are blocked at database query level returning `404 Not Found`.

### Part 3E REST Endpoints

| Method | Endpoint | Description | Role Policy |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/bidder/bids/{bid_id}/readiness` | Granular readiness checklist & missing items summary | `BIDDER` (owner org only) |
| `POST` | `/api/v1/bidder/bids/{bid_id}/submit` | Execute final atomic submission with declaration | `BIDDER` (owner org, `DRAFT` only) |


---

## Bid Document Upload & Management (Part 3D)

Part 3D implements the secure statutory, technical, and commercial document upload pipeline for bidder proposals.

### Key Capabilities & Storage Architecture:

* **Private Storage Abstraction**: Configured for private Supabase Storage bucket `bid-documents` (with local filesystem fallback during offline development). Files are never publicly exposed.
* **MIME & Safe File Extension Validation**: Allowed formats: `.pdf`, `.png`, `.jpg`, `.jpeg`, `.doc`, `.docx`, `.xls`, `.xlsx`. All executables (`.exe`, `.sh`, `.bat`, `.cmd`, `.ps1`, `.vbs`, etc.) are blocked at service and router layers with `400 Bad Request`.
* **File Size Guard**: Enforces strict maximum file size of 10 MB per document. Empty files ($0\text{ bytes}$) are blocked.
* **Tender Requirement Mapping**: Uploaded documents map directly to `tender_requirements.id` or general categories (`STATUTORY`, `TECHNICAL`, `COMMERCIAL`, `OTHER`).
* **Deterministic Auto-Versioning & Replacement**: Uploading a document for an existing requirement automatically archives the previous version as inactive and increments the version counter (`v1` $\rightarrow$ `v2`), preserving an immutable audit trail.
* **Soft Deletion & Mutation Protection**: Active documents can be removed or replaced only while the bid remains in `DRAFT` status. Non-draft bids (`SUBMITTED`, `UNDER_EVALUATION`) reject document mutations with `409 Conflict`.
* **Tenant Isolation & Secure Access**: Only the owning bidder organization can view, list, upload, replace, or download documents. Secure streaming and expiring signed URLs prevent unauthorized cross-tenant exposure.
* **Dynamic Readiness Summary**: Calculates `total_required`, `uploaded_required`, `missing_required`, and `is_ready_for_submission` in real-time.

### Part 3D REST Endpoints

| Method | Endpoint | Description | Role Policy |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/bidder/bids/{bid_id}/documents` | Upload multipart file linked to requirement or general type | `BIDDER` (owner org, `DRAFT` only) |
| `GET` | `/api/v1/bidder/bids/{bid_id}/documents` | List uploaded documents and requirement readiness summary | `BIDDER` (owner org only) |
| `GET` | `/api/v1/bidder/bids/{bid_id}/documents/{document_id}` | Retrieve individual document metadata | `BIDDER` (owner org only) |
| `GET` | `/api/v1/bidder/bids/{bid_id}/documents/{document_id}/download` | Stream binary document file | `BIDDER` (owner org only) |
| `GET` | `/api/v1/bidder/bids/{bid_id}/documents/{document_id}/download-url` | Generate temporary signed download URL | `BIDDER` (owner org only) |
| `PUT` | `/api/v1/bidder/bids/{bid_id}/documents/{document_id}` | Replace existing active document with a new file | `BIDDER` (owner org, `DRAFT` only) |
| `DELETE` | `/api/v1/bidder/bids/{bid_id}/documents/{document_id}` | Soft-remove document from active bid proposal | `BIDDER` (owner org, `DRAFT` only) |


---

## Bid Creation & Tender Participation (Part 3C)

Part 3C enables authenticated `BIDDER` users to participate in `OPEN` procurement tenders by creating and managing draft bid proposal workspaces.

### Key Capabilities & Architectural Safeguards:

* **Tender Status Gate**: Participation is strictly restricted to tenders in `OPEN` status. `DRAFT`, `PUBLISHED`, `CLOSED`, `AWARDED`, and `ARCHIVED` tenders reject bid initiation with clean validation errors.
* **Server-Side Deadline Verification**: Independent server-side UTC clock verification prevents bidding on expired tenders.
* **One-Bid-Per-Tender Rule**: Enforced at the database layer via unique constraint `uq_bids_tender_organization(tender_id, bidder_organization_id)` and service layer checks returning `409 Conflict`.
* **Statutory Profile Readiness Gate**: Bidders must have 100% profile completeness (all 9 statutory fields: PAN, Address, PIN, Contact, etc.) before initiating bids.
* **Deterministic Bid Number Generation**: Sequential unique references formatted as `BID-YYYY-XXXXXX`.
* **Draft Bid Workspace**: Interactive workspace allowing bidders to author and save commercial quotes, currency terms, technical offering summaries, and delivery remarks.
* **Strict Tenant Isolation**: Cross-bidder access is rejected at database and route levels returning `404 Not Found`.

### Part 3C Endpoints

| Method | Endpoint | Description | Role Policy |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/bidder/tenders/{tender_id}/bids` | Create `DRAFT` bid record for `OPEN` tender | `BIDDER` (100% complete profile required) |
| `GET` | `/api/v1/bidder/tenders/{tender_id}/bid` | Query existing bid status for a tender | `BIDDER` |
| `GET` | `/api/v1/bidder/bids` | List bids belonging to authenticated bidder organization | `BIDDER` |
| `GET` | `/api/v1/bidder/bids/{bid_id}` | Retrieve draft bid workspace details | `BIDDER` (owner org only) |
| `PATCH` | `/api/v1/bidder/bids/{bid_id}` | Update commercial and technical draft response | `BIDDER` (`DRAFT` only) |

---


## Bidder Tender Discovery (Part 3B)

Part 3B enables authenticated `BIDDER` users to discover, search, filter, and inspect procurement opportunities across all government buyers.

### Visibility Rules & Role Isolation

* **Visible Tenders**: Tenders in `OPEN` (Active for bidding) and `PUBLISHED` (Upcoming notices) status.
* **Strictly Hidden**: `DRAFT` (Private to creating buyer org) and `ARCHIVED` (soft-deleted) tenders are completely excluded from discovery lists and return `404 Not Found` if accessed directly.
* **Cross-Organization Discovery**: Bidders have platform-wide discovery across all procuring entities and buyer organizations.
* **Sensitive Field Protection**: Internal metadata (Procurement Officer personal email, creator profile IDs, scoring weight coefficients) is omitted from bidder responses.

### Bidder Tender Discovery Endpoints

| Method | Endpoint | Description | Role Policy |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/bidder/tenders` | Search, filter, and paginate available `OPEN` and `PUBLISHED` tenders | Strict `BIDDER` |
| `GET` | `/api/v1/bidder/tenders/{id}` | Retrieve detailed view with sanitized, human-readable eligibility rules | Strict `BIDDER` |

### Condition Formatting Engine

Rule conditions are automatically converted to natural human language for bidders:
* `EQUALS ACTIVE` → *"Must be Active & Verified"*
* `GREATER_THAN_OR_EQUAL 25000000` → *"Minimum required: 25000000"*
* `EXISTS` → *"Mandatory Document / Proof Submission Required"*
* `BLACKLIST EQUALS false` → *"Bidder must not be blacklisted or debarred by GeM / Government"*


---

## Bidder Profile & Organization Setup (Part 3A)

Part 3A establishes the bidder's verified legal entity and authorized signatory identity for procurement participation.

### Supported Fields & Identifiers

* **Organization Information**: Legal Business Name, Trade Name, Organization Type (`PROPRIETORSHIP`, `PARTNERSHIP`, `LLP`, `PRIVATE_LIMITED`, `PUBLIC_LIMITED`, `GOVERNMENT_ENTITY`, `STARTUP`, `OTHER`), MSME Category (`MICRO`, `SMALL`, `MEDIUM`, `LARGE`, `OEM`, `TRADER`, `SERVICE_PROVIDER`, `OTHER`), Year Established, Website, Official Phone, Official Email.
* **Registered Business Address**: Address Line, City, State, PIN Code (6-digit format validation), Country (default: India).
* **Statutory Identifiers**:
  * **PAN Number**: 10-character uppercase alphanumeric (Regex validated: `^[A-Z]{5}[0-9]{4}[A-Z]{1}$`).
  * **GSTIN**: 15-character uppercase format (Regex validated: `^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$`).
  * **Udyam Registration**: MSME identity (`UDYAM-XX-00-0000000`).
  * **CIN / LLPIN**: Corporate Identification Number for MCA entities.
  * **Startup India (DPIIT)**: Recognition number.
  * **NSIC Registration**: National Small Industries Corporation number.
  * **EPFO Code & ESIC Code**: Labour welfare employer codes.
* **Signatory Contact**: Full Name, Designation (e.g. Director, Partner, Authorized Signatory), Phone Number, Immutable Account Email.

> **Statutory Notice**: Registration identifiers in Part 3A are normalized and format-validated. Official automated verification against MCA/GSTN/Udyam portal APIs occurs during the compliance verification stage (Part 5).

### Bidder Profile REST Endpoints

| Method | Endpoint | Description | Role Policy |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/bidder/profile` | Retrieve contact details, organization summary, and profile completion stats | Strict `BIDDER` (own profile only) |
| `PATCH` | `/api/v1/bidder/profile` | Update authorized signatory contact info (`full_name`, `phone`, `designation`) | Strict `BIDDER` (own profile only) |
| `GET` | `/api/v1/bidder/organization` | Retrieve full organization details, statutory credentials, and completion stats | Strict `BIDDER` (own org only) |
| `PATCH` | `/api/v1/bidder/organization` | Update business details and statutory identifiers (with duplicate conflict checks) | Strict `BIDDER` (own org only) |

### Profile Completion Rules

The backend service calculates profile completion dynamically based on 9 mandatory compliance items:
1. Legal Business Name
2. Organization Type
3. Registered Address
4. City
5. State
6. Postal PIN Code
7. Contact Person Name
8. Contact Phone Number
9. PAN Number

Profiles achieve `100% Complete` status only when all 9 items are provided and valid.


---

## Tender Lifecycle State Machine (Part 2E)

The lifecycle of every tender is strictly controlled by a backend state machine service (`app/services/tender_lifecycle_service.py`). Illegal transitions, cross-organization status mutations, and unauthorized bidder mutations are rejected with explicit `409 Conflict` or `403 Forbidden` responses.

```text
       ┌──────────┐
       │  DRAFT   │──────────────┐
       └────┬─────┘              │
            │ Publish            │
            ▼                    │
       ┌──────────┐              │
       │PUBLISHED │──────────────┤
       └────┬─────┘              │
            │ Open for Bidding   │
            ▼                    │
       ┌──────────┐              │
       │   OPEN   │              │
       └────┬─────┘              │
            │ Close Bidding      │
            ▼                    │
       ┌──────────┐              │
       │  CLOSED  │              │
       └────┬─────┘              │
            │ Start Evaluation   │
            ▼                    │
┌──────────────────────┐         │
│  UNDER_EVALUATION    │─────────┤
└───────────┬──────────┘         │
            │ Award              │
            ▼                    │
       ┌──────────┐              │
       │ AWARDED  │──────────────┤
       └──────────┘              │
                                 ▼ Archive
                           ┌───────────┐
                           │ ARCHIVED  │ (Terminal State)
                           └───────────┘
```

### Transition Rules & Allowed Targets

| Current Status | Allowed Next Transitions | Validation / Readiness Prerequisites | Editing & Requirement Policy |
| :--- | :--- | :--- | :--- |
| **`DRAFT`** | `PUBLISHED`, `ARCHIVED` | Valid future submission dates, required metadata, at least 1 active requirement rule | **Full Edit Allowed** (Tender details & requirements) |
| **`PUBLISHED`** | `OPEN`, `ARCHIVED` | Ready for bidding launch | **Locked** (Read-only details & requirements) |
| **`OPEN`** | `CLOSED` | Bidding active (bid submission opens in Part 3) | **Locked** (Immutable requirements to protect bidders) |
| **`CLOSED`** | `UNDER_EVALUATION` | Bid submission window elapsed | **Locked** |
| **`UNDER_EVALUATION`** | `AWARDED`, `ARCHIVED` | Compliance engine verification (Part 5/6) | **Locked** |
| **`AWARDED`** | `ARCHIVED` | Contract award finalized | **Locked** |
| **`ARCHIVED`** | *None (Terminal)* | Soft-deleted / immutable audit record | **Read-Only / Closed** |

---

## Lifecycle API Reference (Part 2E)

All tender lifecycle mutations are served under `/api/v1/tenders/{tender_id}/transition`:

| Method | Endpoint | Payload | Description | Role Policy |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/tenders/{id}/transition` | `{"target_status": "PUBLISHED"}` | Advance tender lifecycle according to state machine rules | `PROCUREMENT_OFFICER` (owner org) |
| `DELETE` | `/api/v1/tenders/{id}` | *None* | Soft-deletes and transitions tender to `ARCHIVED` | `PROCUREMENT_OFFICER` (owner org) |
| `GET` | `/api/v1/tenders/{id}` | *None* | Includes `status`, audit timestamps, and `allowed_transitions: [...]` | Authenticated |

---

## Dynamic Eligibility & Compliance Rule Architecture (Part 2D)

Compliance requirements and eligibility rules are configured dynamically as structured rule data in the database rather than hardcoded logic. Future automated Compliance Engines evaluate bidder document submissions against these condition records.

### Supported Rule Categories & Operators

* **Categories**: `STATUTORY`, `FINANCIAL`, `TECHNICAL`, `EXPERIENCE`, `LOCAL_CONTENT`, `DOCUMENT`, `BLACKLISTING`, `OTHER`.
* **Data Types**: `BOOLEAN`, `NUMBER`, `TEXT`, `DATE`, `DOCUMENT`, `STATUS`.
* **Operators**: `EQUALS`, `NOT_EQUALS`, `GREATER_THAN`, `GREATER_THAN_OR_EQUAL`, `LESS_THAN`, `LESS_THAN_OR_EQUAL`, `CONTAINS`, `EXISTS`, `NOT_EXISTS`.
* **Pre-built Templates**: Valid GST (`ACTIVE`), PAN Document (`EXISTS`), Udyam MSME (`ACTIVE`), OEM Authorization MAF (`EXISTS`), Make in India Local Content (`>= 50%`), Minimum Annual Turnover (`>= ₹5 Cr`), Prior Experience (`>= 3 Yrs`), Non-Debarment Undertaking (`= false`).

---

## Technology Stack

* **Frontend**: Next.js 16 (App Router + Turbopack), React 19, TypeScript, Tailwind CSS v4, Lucide React
* **Backend**: Python 3.10+, FastAPI, Pydantic v2, Pydantic-Settings, Uvicorn
* **Database**: PostgreSQL (hosted on Supabase)
* **ORM & Migrations**: SQLAlchemy 2.x, Alembic, psycopg3 driver
* **Security & Auth**: PyJWT, bcrypt, Bearer token authorization

---

## System Roles & Route Directory

| Role | Portal Home | Sub-Routes | Access Policy |
| :--- | :--- | :--- | :--- |
| **`BIDDER`** | [`/bidder`](http://localhost:3000/bidder) | `/bidder/profile`, `/bidder/organization`, `/bidder/tenders`, `/bidder/bids`, `/bidder/documents`, `/bidder/verification`, `/bidder/clarifications`, `/bidder/notifications` | Strict `BIDDER` role |
| **`PROCUREMENT_OFFICER`** | [`/procurement`](http://localhost:3000/procurement) | `/procurement/tenders`, `/procurement/tenders/new`, `/procurement/tenders/[id]`, `/procurement/tenders/[id]/edit`, `/procurement/bidders`, `/procurement/evaluations`, `/procurement/compliance`, `/procurement/verifications`, `/procurement/clarifications`, `/procurement/reports` | Strict `PROCUREMENT_OFFICER` role |
| **`ADMIN`** | [`/admin`](http://localhost:3000/admin) | `/admin/users`, `/admin/organizations`, `/admin/roles`, `/admin/settings`, `/admin/integrations` | Strict `ADMIN` role |

---

## Development Test Credentials

Run the provisioning scripts if starting on a fresh database:
```bash
python backend/scripts/create_test_users.py
python backend/scripts/seed_tender_demo.py
```

| Role | Email | Password | Assigned Portal |
| :--- | :--- | :--- | :--- |
| **`BIDDER`** | `bidder@test.local` | `TestPassword123!` | `/bidder` |
| **`PROCUREMENT_OFFICER`** | `procurement@test.local` | `TestPassword123!` | `/procurement` |
| **`ADMIN`** | `admin@test.local` | `TestPassword123!` | `/admin` |

---

## Developer Startup Instructions

### Terminal 1: Backend API Service
```powershell
cd backend
venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
python scripts/seed_roles.py
python scripts/create_test_users.py
python scripts/seed_tender_demo.py
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
* **API Root**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
* **Interactive Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* **Database Health Check**: [http://127.0.0.1:8000/health/database](http://127.0.0.1:8000/health/database)

### Terminal 2: Frontend Web App
```powershell
cd frontend
npm install
npm run dev
```
* **Web App**: [http://localhost:3000](http://localhost:3000)

### Automated Test Suites
```powershell
cd backend
venv\Scripts\activate
python scripts/test_part4f_master_integration_qa.py
python scripts/test_part4e_structured_extraction.py
python scripts/test_part4d_document_classification.py
python scripts/test_part4c_ocr_preprocessing.py
python scripts/test_part4b_pdf_text_extraction.py
python scripts/test_part4a_document_processing.py
python scripts/test_part3f_bidder_e2e_regression.py
python scripts/test_part2f_full_verification.py
python scripts/test_part1f_integration.py
```

---

## Part 4A: Document Ingestion & Processing Foundation

Part 4A establishes the controlled, tamper-evident ingestion pipeline foundation for all uploaded bid compliance evidence documents.

### Architecture & Pipeline Lifecycle
1. **Document Upload / Replacement**: Every uploaded document automatically provisions a linked `DocumentProcessing` record in `QUEUED` status and `INGESTION` stage.
2. **State & Stage Machine**:
   - `processing_status`: `QUEUED` $\rightarrow$ `PROCESSING` $\rightarrow$ `COMPLETED` / `FAILED` / `NEEDS_REVIEW`
   - `processing_stage`: `INGESTION` $\rightarrow$ `TEXT_EXTRACTION` $\rightarrow$ `OCR` $\rightarrow$ `CLASSIFICATION` $\rightarrow$ `STRUCTURED_EXTRACTION` $\rightarrow$ `COMPLETED`
   - `extraction_method`: `NONE` $\rightarrow$ `DIGITAL_PDF` / `OCR` / `HYBRID`
3. **Storage Verification**: Verifies physical existence in private Supabase Storage / local cache prior to queueing.
4. **Idempotency & History Preservation**: Soft deletions and version replacements preserve historical processing records on previous document versions.
5. **Security**: Strict tenant isolation (Bidder A cannot access or trigger Bidder B's documents $\rightarrow$ 404).

### REST Endpoints
- `GET /api/v1/bidder/bids/{bid_id}/documents/{document_id}/processing`
- `POST /api/v1/bidder/bids/{bid_id}/documents/{document_id}/process`
- `POST /api/v1/bidder/bids/{bid_id}/documents/{document_id}/retry`

---

## Part 4B: PDF Text Extraction with PyMuPDF

Part 4B extracts embedded machine-readable text from digital PDF documents using PyMuPDF (`fitz`), performs conservative normalization preserving statutory identifiers, analyzes text density deterministically, and routes scanned image documents to the OCR stage.

### Architecture & Capabilities
1. **PyMuPDF Engine (`app/services/pdf_extraction_service.py`)**:
   - Memory-safe binary stream extraction (`fitz.open(stream=pdf_bytes, filetype="pdf")`).
   - Page-by-page text extraction preserving traceable boundaries (`--- Page N ---`).
   - Conservative text normalization: cleans excess whitespace while strictly preserving statutory tokens (PAN `ABCDE1234F`, GSTIN `33ABCDE1234F1Z5`, Udyam `UDYAM-TN-00-1234567`, Currency `₹5,00,00,000`, percentages `50%`, dates `2026-08-26`).
2. **Deterministic Text Quality & OCR Routing**:
   - Computes non-whitespace character count and character density per page.
   - Genuine digital PDFs $\rightarrow$ `extraction_method = DIGITAL_PDF`, `processing_stage = CLASSIFICATION`, `raw_text` & `normalized_text` stored.
   - Scanned / image PDFs $\rightarrow$ routed to OCR pipeline (Part 4C).
3. **Error Handling & Safety**:
   - Corrupted PDFs $\rightarrow$ `FAILED` with `PDF_CORRUPTED`.
   - Encrypted/password-protected PDFs $\rightarrow$ `FAILED` with `PASSWORD_PROTECTED_PDF`.
   - Read-only processing: original binary objects in Supabase storage remain immutable.
4. **Extracted Text Preview UI**:
   - Dedicated authenticated endpoint `GET /api/v1/bidder/bids/{bid_id}/documents/{document_id}/extracted-text`.
   - Frontend workspace modal with page count, extraction method, character count, copy-to-clipboard, and formatted preview.

---

## Part 4C: OCR & Image Preprocessing

Part 4C delivers deep-learning optical character recognition (OCR) and computer vision preprocessing with OpenCV for scanned documents, image files (PNG, JPG, JPEG), and hybrid PDFs.

### Architecture & Capabilities
1. **OpenCV Computer Vision Pipeline (`app/services/image_preprocessing_service.py`)**:
   - **High-Fidelity PDF Page Rendering**: PyMuPDF renders pages at 200-300 DPI (`page.get_pixmap(dpi=200)`).
   - **Grayscale Conversion**: `cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)`.
   - **Bilateral Filtering**: Noise reduction that smooths document texture while preserving alphanumeric character strokes.
   - **Adaptive Contrast Enhancement (CLAHE)**: `cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))` enhances faint stamps, faded text, and watermarks.
   - **Sharpness & Focus Telemetry**: Computes Laplacian variance (`cv2.Laplacian().var()`) for blur detection.
2. **Deep-Learning OCR Engine (`app/services/ocr_service.py`)**:
   - Resilient neural OCR model inference tailored for procurement certificates and declarations.
   - **Multi-Page & Hybrid Ingestion**:
     - Evaluates selectable digital text per page.
     - Pure digital pages $\rightarrow$ PyMuPDF digital extraction.
     - Scanned / image pages $\rightarrow$ 200 DPI OpenCV preprocessing & OCR inference.
     - Document-level classification: `DIGITAL_PDF`, `OCR`, or `HYBRID`.
   - **Traceability**: Tracks page boundaries (`--- Page N ---`), text bounding boxes, and confidence scores.
   - **Quality Scoring & Flagging**: Evaluates character density and average confidence. Documents with illegible scans are flagged as `NEEDS_REVIEW` with `OCR_LOW_QUALITY` telemetry.
3. **Strict Compliance & Security**:
   - **Immutable Files**: Original uploaded binary files remain strictly read-only in private storage.
   - **Tenant Isolation**: Bidders can only trigger OCR and inspect extracted text for their own authorized bids (cross-tenant access rejected with 404).
   - **Post-Submission Read Access**: Allows procurement officers and bidders to view extracted text on `SUBMITTED` bids.

---

## Part 4D: Deterministic Document Classification Engine

Part 4D implements a transparent, weighted rule-based classification engine that identifies Indian procurement document types without opaque machine learning or external API dependencies.

### Classification Architecture & Document Classes
1. **Supported Document Classes**:
   - `GST_CERTIFICATE` (Form GST REG-06, Registration Certificate)
   - `PAN` (Income Tax Department Permanent Account Number Card)
   - `UDYAM_CERTIFICATE` (Ministry of MSME Udyam Registration)
   - `INCORPORATION_CERTIFICATE` (MCA Certificate of Incorporation / CIN / LLPIN)
   - `FINANCIAL_STATEMENT` (Balance Sheet, Profit & Loss, CA Audited Turnover)
   - `OEM_AUTHORIZATION` (Manufacturer's Authorization Form / MAF)
   - `LOCAL_CONTENT_DECLARATION` (PPP-MII Class I / Class II Local Content)
   - `EXPERIENCE_CERTIFICATE` (Work Order, Completion Certificate, Supply Proof)
   - `NON_BLACKLISTED_UNDERTAKING` (Debarment / Non-Blacklisting Affidavit)
   - `TECHNICAL_DATASHEET` (Technical Compliance Specification Sheet)
   - `POWER_OF_ATTORNEY` (Board Resolution / Authorized Signatory PoA)
   - `UNKNOWN` (Fallback for unrecognizable or ambiguous documents)
2. **Deterministic Weighted Scoring Engine (`app/services/document_classification_service.py`)**:
   - Primary Statutory Anchors (50-60 pts), Secondary Keyword Tokens (15-20 pts), and Format Context Tokens (10-15 pts).
   - Negative Discriminator Penalties (-40 to -50 pts) to resolve ambiguity between similar documents.
   - Classification Confidence Tiers: `HIGH` ($\ge 0.80$), `MEDIUM` ($0.60 - 0.79$), `LOW` ($< 0.60$).
3. **Requirement Mismatch Review Gate**:
   - Automatically derives expected document type from mapped `TenderRequirement`.
   - Flags discrepancies between uploaded and detected types as `NEEDS_REVIEW` with neutral diagnostic messages (e.g. *"Uploaded document appears to be a PAN Card rather than the expected GST Registration Certificate."*).

---

## Part 4E: Structured Entity & Field Extraction Engine

Part 4E extracts structured, provenance-linked metadata and statutory identifiers from classified procurement documents using regex engines, financial parsers, and date normalizers.

### Key Extraction Capabilities & Provenance Tracking
1. **Statutory & Business Entity Extractors (`app/services/structured_extraction_service.py`)**:
   - **GST Certificate**: GSTIN (`29AABCB1234F1Z5`), Legal Name, Trade Name, Constitution, Registration Date.
   - **PAN Card**: PAN (`ABCDE1234F`), Full Name, Father's Name, Date of Birth / Incorporation.
   - **Udyam MSME**: Udyam Number (`UDYAM-KR-03-0012345`), Enterprise Name, Enterprise Category (`MICRO`/`SMALL`/`MEDIUM`), Major Activity (`MANUFACTURING`/`SERVICES`), Date of Incorporation.
   - **Financial Statement**: Financial Year, Annual Turnover (normalized to numeric float with Indian numbering format: Lakhs/Crores), Net Worth, Profit After Tax, CA Membership Number, UDIN (`18-digit`).
   - **OEM Authorization**: OEM Manufacturer Name, Authorized Bidder Name, Tender Reference, Validity Period.
   - **Local Content Declaration**: Local Content Percentage (`float`), Declaration Class (`CLASS_I` / `CLASS_II`), Manufacturing Location.
   - **Non-Blacklisting Undertaking**: Non-Debarment Affirmation (`boolean`), Execution Date, Signatory Name.
2. **Confidence Scoring & Provenance**:
   - Every extracted field carries metadata: `{"value": ..., "confidence": 0.95, "evidence": "...", "page": 1, "extraction_method": "DIGITAL_PDF"}`.
   - Ambiguous or conflicting values are flagged with `is_conflict=True` and routed to manual review.
3. **Robust Parsers**:
   - Date normalizer supporting DD/MM/YYYY, YYYY-MM-DD, and textual formats (`15th August 2020`).
   - Indian currency parser supporting `₹`, `INR`, `Crores`, `Lakhs`, and standard commas.

---

## Part 4F: Final Document Processing Integration, Review & QA

Part 4F unifies and hardens the entire document processing pipeline from multipart upload to structured field extraction, verifying reliability across digital, scanned, and hybrid files while maintaining strict separation from the compliance evaluation engine.

### Verification Matrix & QA Hardening (12/12 Master QA Criteria)
1. **Digital PDF Flow**: Complete end-to-end processing with PyMuPDF, classification, and structured extraction in $<1.5\text{s}$.
2. **Scanned PDF Flow**: Automatic OCR fallback with OpenCV preprocessing and PaddleOCR inference.
3. **Standalone Image Flow**: High-quality text extraction from PNG/JPG documents.
4. **Hybrid Document Flow**: Deterministic routing processing Page 1 digitally and Page 2 via OCR (`HYBRID`).
5. **Low-Signal & Ambiguity**: Safely marks unrecognizable files as `UNKNOWN` and `NEEDS_REVIEW` without crashing.
6. **Requirement Mismatch Gate**: Flags category mismatches neutrally without premature compliance rejection.
7. **Entity Conflict Detection**: Detects conflicting tokens (e.g. multiple distinct GSTINs) and sets `is_conflict=True`.
8. **Safe Failure Telemetry**: Gracefully handles corrupted PDFs (`PDF_CORRUPTED`), locked PDFs (`PASSWORD_PROTECTED_PDF`), and corrupted images (`IMAGE_DECODE_FAILED`) with actionable error messages.
9. **Idempotency & Retry**: Idempotent re-execution on completed documents and clean state resetting on retry.
10. **Document Replacement & Audit Trail**: Preserves historical processing records on `v1` while independently processing `v2`.
11. **Strict Multi-Tenant Isolation**: Verified `404 Not Found` across all processing telemetry and extracted data endpoints for unauthorized cross-tenant requests.
12. **Compliance Separation Guard**: Strict enforcement ensuring document processing contains **zero** compliance evaluation (`PASS`/`FAIL`, compliance score, risk level, or AI recommendations), remaining purely technical and ready for Part 5.

### Master QA Suite Execution
```powershell
cd backend
venv\Scripts\activate
python scripts/test_part4f_master_integration_qa.py
```
> **Result**: `ALL 12/12 PART 4F MASTER INTEGRATION & QA TESTS PASSED (100% SUCCESS)`

---

## Part 6F: Final Compliance Integration, Rule-by-Rule Results & QA

Part 6F unifies and finalizes the entire Compliance Engine (Parts 6A through 6F) into an enterprise-grade, deterministic, and auditable system operating across all 8 major procurement domains.

### Master QA Matrix & Hardening (12/12 Criteria Validated):
1. **Evaluator Registry Completeness**: All 10 domain-specific and generic compliance evaluators registered in priority order:
   - `StatutoryRuleEvaluator`
   - `IntegrityComplianceEvaluator`
   - `FinancialComplianceEvaluator`
   - `ExperienceComplianceEvaluator`
   - `OEMComplianceEvaluator`
   - `LocalContentComplianceEvaluator`
   - `BISComplianceEvaluator`
   - `TechnicalComplianceEvaluator`
   - `SupportingDocumentEvaluator`
   - `GenericRuleEvaluator`
   - `FallbackUnsupportedEvaluator` (Safe fallback returning `REVIEW`)
2. **Operator Set Correctness**: Comprehensive validation of scalar and presence comparisons (`EQUALS`, `NOT_EQUALS`, `GT`, `GTE`, `LT`, `LTE`, `CONTAINS`, `EXISTS`, `NOT_EXISTS`, `IN`).
3. **Standard Compliance Determinations**: Normalized statuses (`PASS`, `FAIL`, `REVIEW`, `NOT_APPLICABLE`, `PENDING`, `BLOCKED`).
4. **Prerequisite & Source Outage Resilience**: Third-party verification outages (`UNAVAILABLE` / `FAILED`) return `REVIEW` (`review_type="SOURCE_UNAVAILABLE"`) with explanatory reasoning without penalizing bidders.
5. **Critical vs Mandatory Rule Separation**: Fatal disqualifiers (Debarment, Active Blacklisting) flag `critical_failure=True`, cleanly partitioned from standard non-critical mandatory rule failures.
6. **Review Queue Aggregation & Telemetry**: Ambiguous names, format discrepancies, and borderline confidence scores aggregate into `review_items` with standardized `review_type` flags (`NAME_VARIATION`, `VERIFICATION_UNCERTAIN`, etc.).
7. **Multi-Domain Realistic Synthetic Bid End-to-End Evaluation**: Full 10-clause multi-domain test covering Statutory, MSME, Turnover, Experience, Technical, OEM, Local Content, BIS, Debarment, and PAN-GST consistency passing 10/10 with complete provenance.
8. **Evaluation Versioning & Idempotent Audit Trail**: Re-evaluating bids increments `evaluation_version`, marking prior version records `is_current = False` to preserve full immutable audit trails.
9. **Partial Bid & Missing Document Handling**: Bids with missing documents or unverified claims process all active clauses gracefully, assigning `PENDING` or `REVIEW` without crashing.
10. **Multi-Tenant Security & Strict RBAC Isolation**: HTTP 404 response on unauthorized cross-tenant bid compliance queries.
11. **Procurement Officer Compliance Dashboard**: Production Next.js dashboard (`/procurement/compliance`) with interactive Bid UUID search, KPI summary metrics, clause-by-clause audit table, and expandable verification provenance drawer.
12. **Strict Compliance Separation Guard**: Strict enforcement ensuring Part 6 computes **zero** final weighted score (0–100%), **zero** risk level (LOW/MEDIUM/HIGH), **zero** AI recommendations, and **zero** automated award decisions (reserved for Part 7 & Part 8).

### Master QA Suite Execution
```powershell
cd backend
venv\Scripts\activate
python scripts/test_part6f_master_compliance_qa.py
```
> **Result**: `ALL 56/56 PART 6F MASTER COMPLIANCE INTEGRATION & QA TESTS PASSED (100% SUCCESS)`

---

## Part 7A: Scoring Engine Foundation & Weighting Architecture

Part 7A establishes the deterministic, auditable mathematical and architectural foundation for bid compliance scoring in BidVerify AI.

```text
Part 6 Compliance Results
        ↓
Rule Weight Resolution (Tender Configured / Default 10.0)
        ↓
Status-to-Score Factor Mapping (PASS=1.0, FAIL=0.0, PENDING=0.0, REVIEW=Policy)
        ↓
Normalized Rule Contributions (earned_weight = weight × score_factor)
        ↓
Eligible Weight & Earned Weight Aggregation (Decimal Precision 10,4)
        ↓
Scoring Readiness & Completeness Tracking (READY / INCOMPLETE / BLOCKED)
        ↓
Versioned Audit Snapshots (bid_score_snapshots)
        ↓
Ready for Category Scoring in Part 7B
```

### Key Capabilities & Architectural Principles:
1. **Weight Semantics & Resolution**:
   - Preserves configured requirement weights (`TenderRequirement.weight`).
   - Uses centralized default `DEFAULT_REQUIREMENT_WEIGHT = Decimal("10.0")` for unspecified weights.
   - Enforces `weight >= 0`, rejecting negative, NaN, and non-numeric values.
   - Supports `weight = 0` (zero-weighted rules remain visible in audits but contribute `0` to scoring).
2. **Status-to-Score Factor Mappings**:
   - `PASS`: Full credit (`score_factor = 1.0000`, `earned_weight = weight`).
   - `FAIL`: Zero credit (`score_factor = 0.0000`, `earned_weight = 0.0000`).
   - `NOT_APPLICABLE`: Excluded from denominator (`eligible_weight = 0.0000`, `earned_weight = 0.0000`, `excluded_from_score = True`).
   - `PENDING`: Scorable weight preserved in `eligible_weight` with `0.0000` earned, marking `scoring_complete = False` and `scoring_status = INCOMPLETE` (no silent penalty).
   - `REVIEW`: Centralized configurable policy (`ReviewPolicy.UNRESOLVED` default vs `ReviewPolicy.PARTIAL_CREDIT`), setting `human_review_required = True`.
3. **Decimal Precision & Rounding**:
   - 4-decimal fixed-point arithmetic (`Decimal("0.0001")`, `ROUND_HALF_UP`) to eliminate binary floating-point drift.
4. **Safe Denominator & Edge Cases**:
   - Safely returns `NO_SCORABLE_REQUIREMENTS` with zero division immunity when no scorable clauses exist.
5. **Versioned Audit Snapshots (`bid_score_snapshots`)**:
   - Persists recalculations as immutable snapshots incrementing `scoring_version` (`v1` $\rightarrow$ `v2`), marking prior versions `is_current = False`.
   - Snapshots include formula version (`v1.0`), rule counts, readiness telemetry, and granular serialized `rule_contributions`.
6. **Strict RBAC & Tenant Isolation**:
   - Verified `HTTP 404 Not Found` for unauthorized cross-tenant bid score requests across Bidder and Procurement Officer endpoints.
7. **Strict Boundary Compliance**:
   - Zero category percentages, zero final score presentation cards (e.g. "84%"), zero Risk Level assessments, zero critical overrides, and zero AI recommendations (reserved for Parts 7B–7E).

### Master QA Suite Execution
```powershell
cd backend
venv\Scripts\activate
python scripts/test_part7a_scoring_foundation.py
```
> **Result**: `ALL 21/21 PART 7A MASTER SCORING FOUNDATION TESTS PASSED (100% SUCCESS)`

---

## Part 7B: Category-wise Compliance Scoring

Part 7B aggregates rule-level weighted contributions into deterministic, auditable **Category Scores** and an **Overall Compliance Score** across all GeM procurement domains.

```text
Part 6 Compliance Results
        ↓
Part 7A Rule Contributions
        ↓
Group by Domain Category (STATUTORY, FINANCIAL, EXPERIENCE, TECHNICAL, OEM, LOCAL_CONTENT, BIS, DOCUMENTS, INTEGRITY)
        ↓
Category Earned Weight / Eligible Weight
        ↓
Category Score = (category_earned_weight / category_eligible_weight) × 100
        ↓
Overall Total Earned Weight / Overall Total Eligible Weight
        ↓
Overall Compliance Score = (total_earned_weight / total_eligible_weight) × 100
        ↓
Ready for Part 7C Risk Assessment
```

### Key Capabilities & Architectural Principles:
1. **Weighted Category Scoring Formula**:
   - For each category: `category_score = (category_earned_weight / category_eligible_weight) × 100`.
   - Category scores strictly reflect individual clause weights (`TenderRequirement.weight`), avoiding unweighted rule counting.
2. **Overall Compliance Score**:
   - Computed strictly as `overall_score = (total_earned_weight / total_eligible_weight) × 100`.
   - **Critical Principle**: Avoids the "blind category average trap" (e.g. Cat A 100% on wt 10 + Cat B 50% on wt 90 yields `55.00%`, NOT `75.00%`).
3. **Zero Denominator Immunity**:
   - If `category_eligible_weight == 0` (e.g. all rules in category are `NOT_APPLICABLE` or zero-weighted), `score = None` rather than misleading `0%`.
4. **Provisional Score Handling**:
   - If any applicable rule is `PENDING`, `scoring_complete = False` and `is_provisional = True`, labeled as "Provisional Compliance Score" in the UI.
5. **Metadata Preservation**:
   - Preserves `mandatory_failures` and `critical_failures` counts per category and overall without prematurely applying caps/overrides (reserved for Part 7D).
6. **Snapshot Persistence & Database Schema**:
   - Added `overall_score` (Numeric 5,2), `is_provisional` (Boolean), and `category_scores` (JSONB) to `bid_score_snapshots` table via Alembic migration `016_add_category_scoring_fields.py`.
7. **Frontend Scoring Overview**:
   - Interactive Procurement Officer dashboard with overall compliance score banner, provisional alert warnings, visual progress bars, and domain-by-domain score cards grid.
8. **Strict Architectural Boundaries**:
   - Zero Risk Levels (`LOW`/`MEDIUM`/`HIGH`), zero critical overrides/caps, zero AI recommendations, and zero automated award decisions.

### Master QA Suite Execution
```powershell
cd backend
venv\Scripts\activate
python scripts/test_part7b_category_scoring.py
```
> **Result**: `ALL 23/23 PART 7B MASTER CATEGORY SCORING TESTS PASSED (100% SUCCESS)`

---

## Part 7C: Deterministic Risk Assessment Engine

Part 7C implements a deterministic, multi-factor mathematical base risk engine that quantifies proposal uncertainty, clause non-compliance, and evidence inconsistencies.

```text
Part 6 Compliance Results + Part 7B Compliance Score
        ↓
Feature Extraction (Compliance Score Deficit, Failure Rate, Review Uncertainty, Mandatory Fails, Integrity Findings)
        ↓
Weighted Indicator Contributions (0-100 Mathematical Scale)
        ↓
Score Clamping & Half-Open Threshold Boundaries ([0-25) LOW, [25-50) MEDIUM, [50-75) HIGH, [75-100] CRITICAL)
        ↓
Provisional Handling for Pending Verification Checks
        ↓
Immutable Risk Snapshot Persistence (bid_risk_snapshots)
        ↓
Ready for Part 7D Critical Overrides
```

### Key Capabilities & Architectural Principles:
1. **Explainable Base Risk Decomposition**:
   - `COMPLIANCE_SCORE_DEFICIT`: Proportional to `(100 - compliance_score)`.
   - `FAILURE_RATE`: Ratio of failed clauses to total evaluated clauses.
   - `REVIEW_UNCERTAINTY_RATE`: Partial risk contribution for clauses requiring human review.
   - `MANDATORY_FAILURES`: Additional weighted penalty for non-compliant mandatory requirements.
   - `INTEGRITY_MISMATCH`: Risk points for cross-document identity or blacklisting anomalies.
2. **Deterministic Threshold Classifications**:
   - `LOW`: `0.00 <= risk_score < 25.00`
   - `MEDIUM`: `25.00 <= risk_score < 50.00`
   - `HIGH`: `50.00 <= risk_score < 75.00`
   - `CRITICAL`: `75.00 <= risk_score <= 100.00`
3. **Provisional Uncertainty Safeguards**:
   - Any unresolved `PENDING` checks set `risk_complete = False` and `is_provisional = True` without false penalties.
4. **Strict Architectural Boundaries**:
   - Base risk calculation does not apply hard critical overrides or automated qualification decisions (reserved for Part 7D & 8D).

### Master QA Suite Execution
```powershell
cd backend
venv\Scripts\activate
python scripts/test_part7c_risk_engine.py
```
> **Result**: `ALL 21/21 PART 7C MASTER RISK ENGINE TESTS PASSED (100% SUCCESS)`

---

## Part 7D: Critical Overrides & Risk Adjustments

Part 7D introduces rule-based critical floors and risk adjustments that enforce public procurement integrity mandates without downgrading higher mathematical base risk.

```text
Base Mathematical Risk (Part 7C)
        ↓
Critical Floor Rules Evaluation (Blacklisting, Active Debarment, Critical Clause Failures, PAN/GST Inconsistency)
        ↓
Precedence Resolution: max(base_risk_score, max(applicable_floors))
        ↓
Escalation Mapping (Active Blacklist -> Floor 90.0 CRITICAL; Multiple Critical Fails -> Floor 80.0 CRITICAL)
        ↓
Override Audit Logging & Traceable Evidence Attachment
        ↓
Versioned Snapshot Update (is_current = True)
```

### Key Capabilities & Architectural Principles:
1. **Critical Risk Floors**:
   - **Active Blacklisting / Debarment**: Applies minimum floor `90.00` (`CRITICAL`).
   - **Single Critical Requirement Failure** (e.g. OEM Authorization): Applies floor `70.00` (`HIGH`).
   - **Multiple Critical Failures** ($\ge 2$): Escalates floor to `80.00` (`CRITICAL`).
   - **Severe Structural Mismatch** (PAN/GST): Applies floor `75.00` (`CRITICAL`).
2. **Never Downgrade Invariant**:
   - If base mathematical risk is already higher than an applicable floor, the higher score is preserved (`max` semantics).
3. **Audit Trail & Traceability**:
   - Persists all applied override triggers, initial vs adjusted scores, and explanatory rationale directly in `applied_overrides` JSONB.

### Master QA Suite Execution
```powershell
cd backend
venv\Scripts\activate
python scripts/test_part7d_override_engine.py
```
> **Result**: `ALL 21/21 PART 7D MASTER OVERRIDES & RISK ADJUSTMENT TESTS PASSED (100% SUCCESS)`

---

## Part 7E: RAG + AI Recommendation & Evidence-Based Explanation

Part 7E implements grounded Retrieval-Augmented Generation (RAG) using `pgvector` dense embeddings, prompt injection containment, deterministic guardrails, and citation verification.

```text
Bid Documents + Verifications + Compliance + Scores + Risk
        ↓
Semantic Chunking & Embedding Generation (1536-dim vector indexing)
        ↓
Tenant & Bid-Scoped Hybrid Retrieval (Dense Vector + Metadata Filters)
        ↓
Prompt Injection Containment Boundary & Evidence Formulation
        ↓
LLM Synthesis (Executive Summary, Key Strengths, Concerns, Review Items)
        ↓
Deterministic Guardrail Enforcement (Never recommend PROCEED on CRITICAL risk)
        ↓
Citation ID Verification (Prune ungrounded/hallucinated references)
        ↓
AI Recommendation Record Persistence (ai_recommendations)
```

### Key Capabilities & Architectural Principles:
1. **Full Knowledge Indexing**:
   - Indexes tender clauses, bid documents, OCR extractions, statutory verifications, compliance outcomes, and risk snapshots into `rag_chunks` with `pgvector`.
2. **Strict Multi-Tenant Scoped Retrieval**:
   - All vector queries enforce `bid_id` and `organization_id` filters to eliminate cross-bid data leakage.
3. **Prompt Injection Defense**:
   - Wraps bidder-supplied text inside sanitized, delimited context blocks with strict system instructions prohibiting directive execution from document content.
4. **Deterministic Guardrail Overrides**:
   - AI recommendations cannot contradict deterministic risk levels (e.g. downgrades `PROCEED` to `DO_NOT_PROCEED_WITHOUT_REVIEW` if risk is `CRITICAL`).
5. **Hallucination Pruning & Grounded Q&A**:
   - Verifies citation IDs against active evidence chunks, stripping ungrounded references.
   - Interactive Q&A console answers procurement officer inquiries with exact evidence provenance.

### Master QA Suite Execution
```powershell
cd backend
venv\Scripts\activate
python scripts/test_part7e_rag_ai_engine.py
```
> **Result**: `ALL 21/21 PART 7E MASTER RAG & AI ENGINE TESTS PASSED (100% SUCCESS)`

---

## Part 7F: Unified Bid Evaluation Integration

Part 7F coordinates the authoritative evaluation summary combining Compliance, Category Scoring, Risk Assessments, Overrides, and AI Recommendations into a single unified API and UI interface.

```text
[Part 6 Compliance] + [Part 7A/7B Score] + [Part 7C/7D Risk] + [Part 7E AI Recommendation]
                                    ↓
                 Bid Evaluation Service (Unified Orchestrator)
                                    ↓
               Staleness Detection across Dependency Chain
                                    ↓
       Deterministic Recalculation vs Explicit AI Regeneration Endpoints
                                    ↓
           Full Audit Traceability (Clause -> Doc -> Ver -> Score -> Risk -> AI)
                                    ↓
       Procurement Evaluation UI (/procurement/evaluations & /procurement/tenders/[id]/bids/[bidId]/evaluation)
```

### Key Capabilities & Architectural Principles:
1. **Unified Evaluation Payload**:
   - Aggregates compliance counts, category score breakdown, base/adjusted risk scores, critical findings, review items, and AI analysis into `BidEvaluationSummaryResponse`.
2. **Granular Staleness Detection**:
   - Automatically detects when upstream compliance changes invalidate downstream score (`SCORE`), risk (`RISK`), or AI (`AI`) assessments.
3. **Decoupled Refresh Workflows**:
   - **Deterministic Refresh**: Instantaneous mathematical recalculation of scores and risk without calling the LLM.
   - **AI Regeneration**: Explicit trigger that re-indexes vector knowledge and regenerates AI synthesis.
4. **Strict Separation of Duties**:
   - `final_decision_status` remains `NOT_MADE`; automated qualification is strictly prohibited. AI never alters deterministic score or risk records.

### Master QA Suite Execution
```powershell
cd backend
venv\Scripts\activate
python scripts/test_part7f_unified_evaluation.py
```
> **Result**: `ALL 21/21 PART 7F MASTER UNIFIED EVALUATION TESTS PASSED (100% SUCCESS)`

---

## Part 8A: Procurement Evaluation Dashboard Foundation

Part 8A provides the command center for Procurement Officers, featuring aggregate KPI metrics, tender evaluation progress tracking, and multi-dimensional bid evaluation matrices.

```text
Procurement Officer Authentication & Org Scope
        ↓
Procurement Dashboard Service (/api/v1/procurement/dashboard)
        ↓
Aggregate KPI Telemetry (Active Tenders, Submitted Bids, Review Required, Critical Risk, Completed)
        ↓
Per-Tender Evaluation Listing (/api/v1/procurement/tenders/{id}/evaluations)
        ↓
Multi-Field Search (Legal Name, Trade Name, Bid #, PAN, GSTIN)
        ↓
Multi-Dimensional Filtering (Status, Risk Level, Review Required, Critical Only, AI Recommendation)
        ↓
Safe Numerical & Date Sorting + Server-Side Pagination
        ↓
Next.js 16 Command Center UI (/procurement & /procurement/tenders/[id]/evaluation)
```

### Key Capabilities & Architectural Principles:
1. **Procurement Command Center KPIs**:
   - Real-time aggregation of active tenders, submitted bids, pending evaluations, review-required flags, and critical risk counts.
2. **Tender Bid Evaluation Matrix**:
   - Paginated list of submitted bids per tender displaying legal/trade name, bid number, compliance score, adjusted risk level, review counts, AI recommendation, and derived evaluation status.
3. **Multi-Field Search & Multi-Dimensional Filters**:
   - Instant search by bidder name, bid number, or tax identifiers (PAN/GSTIN).
   - Filtering by evaluation status (`EVALUATION_COMPLETE`, `PROVISIONAL`, `REVIEW_REQUIRED`, `AI_STALE`), risk level (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`), and AI recommendation.
4. **Safe Sorting & Pagination**:
   - Type-safe sorting across compliance score, adjusted risk score, review items count, and submission date with null-safe handling.

### Master QA Suite Execution
```powershell
cd backend
venv\Scripts\activate
python scripts/test_part8a_dashboard_foundation.py
```
> **Result**: `ALL 21/21 PART 8A MASTER PROCUREMENT DASHBOARD TESTS PASSED (100% SUCCESS)`

---

## Part 8B: Bid Comparison & Shortlisting View

Part 8B implements side-by-side multi-bid comparative evaluations, clause-by-clause difference detection, category matrices, and human-controlled shortlisting workflows for Procurement Officers.

```text
Tender Evaluation Matrix (/procurement/tenders/[id]/evaluation)
        ↓ (Select 2 to 5 submitted bids via checkboxes)
POST /api/v1/procurement/tenders/{id}/compare-bids
        ↓
Bid Comparison Service (Strict same-tender validation, Batch query optimization)
        ↓
Side-by-Side Comparative Matrix:
  ├─ Summary Metrics (Score, Risk, Overrides, Defect Counts, AI Advice)
  ├─ Category Breakdown Matrix (Statutory, Financial, Experience, OEM, etc.)
  ├─ Critical Findings & Risk Floor Overrides Comparison
  └─ Clause-by-Clause Requirement Comparison (all_match Difference Highlighting)
        ↓
Human-Controlled Shortlisting Workflows:
  ├─ POST /api/v1/procurement/tenders/{id}/bids/{bidId}/shortlist (Add with Rationale)
  ├─ DELETE /api/v1/procurement/tenders/{id}/bids/{bidId}/shortlist (Remove with Reason)
  └─ GET /api/v1/procurement/tenders/{id}/evaluations?shortlisted_only=true
        ↓
Next.js 16 Responsive UI (/procurement/tenders/[id]/compare)
```

### Key Capabilities & Architectural Principles:
1. **Strict Same-Tender Scoping**:
   - Only bids submitted for the exact same `tender_id` can be compared (minimum 2, maximum 5). Cross-tender comparison attempts are rejected with `HTTP 400 Bad Request`.
2. **Side-by-Side Comparative Matrix**:
   - Compares overall compliance scores, deterministic adjusted risk scores, critical override floors, mandatory failure counts, human review counts, and AI recommendations in a synchronized horizontal view.
3. **Category Performance Comparison**:
   - Side-by-side category score evaluation. When a category has zero scorable rules for a bid, it is safely marked `N/A` (never falsely displaying `0%`).
4. **Clause-by-Clause Difference Detection (`all_match`)**:
   - Compares bidder determinations per tender requirement clause. Highlights differences when bids have contrasting determinations (`PASS` vs `FAIL`/`REVIEW`).
5. **Human-Controlled Shortlisting with Audit Trail**:
   - Procurement Officers can mark/unmark bids as shortlisted with required remarks/rationales.
   - Preserves audit provenance (`shortlisted_by_id`, `updated_at`, `reason`).
   - Shortlisting does **not** change bid status (`SUBMITTED`) or make automated qualification/award decisions (reserved for Part 8D).
6. **Zero N+1 Query Batch Execution**:
   - Single batch query fetch for bids, requirements, compliance results, score snapshots, risk snapshots, AI records, and shortlist state.

### Master QA Suite Execution
```powershell
cd backend
venv\Scripts\activate
python scripts/test_part8b_bid_comparison.py
```
> **Result**: `ALL 21/21 PART 8B MASTER BID COMPARISON & SHORTLISTING TESTS PASSED (100% SUCCESS)`

---

## Part 8C: Human Review & Evidence Inspection Workflow

Part 8C provides a dedicated, auditable evidence inspection workspace where authorized Procurement Officers can review flagged discrepancies, inspect source documents and OCR confidence, evaluate cross-document entity consistency, add chronological notes, and resolve review items with automatic downstream Score/Risk recalculations and AI staleness invalidation.

```text
Procurement Officer Review Queue (/procurement/reviews)
        ↓ (Select flagged review item)
GET /api/v1/procurement/reviews/{review_id}
        ↓
Comprehensive Evidence Inspection Workspace (/procurement/reviews/[reviewId]):
  ├─ Panel 1: Requirement Clause & Target Criteria (Operator, Expected, Mandatory, Critical)
  ├─ Panel 2: Actual vs Expected Evidence Determination (Claimed vs Verified, Match Status)
  ├─ Panel 3: Source Document & Extraction Provenance (Page #, Extracted Snippet, OCR Confidence)
  ├─ Panel 4: External Verification & Sandbox Transparency (Source Registry, Mock Warning, Match Status)
  ├─ Panel 5: Cross-Document Identity Comparison (PAN Document vs GSTIN vs MCA Entity Name)
  ├─ Panel 6: Advisory AI Explanation (Grounded Citations, Advisory Disclaimer, Stale Indicator)
  ├─ Panel 7: Auditable Reviewer Notes Thread (Author, Timestamp, Role, Append Form)
  └─ Panel 8: Controlled Human Resolution Workspace (CONFIRMED, REJECTED, NEEDS_MORE_EVIDENCE, ESCALATED)
        ↓
POST /api/v1/procurement/reviews/{review_id}/resolve
        ↓
Atomic Audit Update & Downstream Orchestration:
  ├─ Update HumanReviewItem (status=RESOLVED, resolution, reason, resolved_by, resolved_at)
  ├─ Update ComplianceResult (effective_status=PASS/FAIL, evidence["human_resolution"] provenance)
  ├─ Deterministic Score & Risk Recalculation (calculate_and_save_bid_score & calculate_and_save_bid_risk)
  └─ Flag Downstream AI Recommendation as STALE (without invoking expensive LLMs)
```

### Key Capabilities & Architectural Principles:
1. **Dedicated Human Review Queue**:
   - Centralized workspace at `/procurement/reviews` for Procurement Officers with real-time KPI metrics (`total_open`, `critical_open`, `in_review`, `resolved_today`, `escalated`), search across vendors/clauses/IDs, and multi-dimensional filters.
2. **Deep Evidence Provenance & Transparency**:
   - Displays source document metadata, page number tags, extracted snippets, and OCR extraction confidence.
   - External registry verification results clearly flag mock/sandbox telemetry to prevent false impressions of live government queries.
3. **Cross-Document Identity Consistency**:
   - Compares PAN credentials against GSTIN embedded PAN and MCA entity names with automated match/mismatch indicators.
4. **Advisory AI Grounding**:
   - AI recommendations remain strictly advisory with an immutable disclaimer. AI cannot resolve reviews or alter deterministic records.
5. **Auditable Reviewer Notes**:
   - Preserves an immutable, chronological history of remarks with author identity, role, and timestamps without overwriting previous entries.
6. **Controlled Human Resolution**:
   - Supported resolution outcomes: `CONFIRMED` (effective `PASS`), `REJECTED` (effective `FAIL`), `NEEDS_MORE_EVIDENCE` (remains in review), `ESCALATED`, and `NOT_APPLICABLE`.
   - Mandatory factual justification (minimum 5 characters) is required for resolution.
   - Original system calculation snapshot is strictly preserved alongside the human resolution and effective determination.
7. **Downstream Recalculation & Staleness**:
   - Resolving a review item immediately triggers deterministic Score and Risk recalculations so evaluation dashboards reflect updated numbers, and flags AI recommendations as stale.
8. **Strict Multi-Tenant Isolation & Role Invariants**:
   - Cross-tenant access is blocked with `HTTP 404/403`.
   - Bidders are strictly forbidden (`HTTP 403 Forbidden`).
   - Human review resolution does **not** change bid status (`SUBMITTED`) or make final qualification/award decisions (reserved for Part 8D).

### Master QA Suite Execution
```powershell
cd backend
venv\Scripts\activate
python scripts/test_part8c_human_review.py
```
> **Result**: `ALL 27/27 PART 8C MASTER HUMAN REVIEW & EVIDENCE INSPECTION TESTS PASSED (100% SUCCESS)`

---

## Final Human Decision Workflow (Part 8D)

Part 8D delivers an authoritative, auditable human-controlled final decision workflow for Procurement Officers to record and manage qualification determinations (`NOT_DECIDED`, `UNDER_REVIEW`, `QUALIFIED`, `DISQUALIFIED`), protected by platform readiness safeguards, decision versioning with superseding, snapshot auditing, and staleness detection upon upstream evaluation mutations:

> [!IMPORTANT]
> **Strict Human Agency & Zero Automated Award Invariant**: Final qualification determinations are strictly reserved for authorized Procurement Officers and Admins. AI provides advisory compliance scores, risk levels, and synthesis, but **never** makes, alters, or triggers qualification decisions.
> `QUALIFIED` indicates eligibility to proceed to the next procurement stage. It does **not** mutate `Bid.status` away from `SUBMITTED`, nor does it mutate `Tender.status` to `AWARDED`.

```text
Unified Evaluation Summary (Score, Risk, Overrides, AI)
        +
Live Human Review Queue (Open & Critical Items)
        ↓
Decision Readiness Evaluation (get_decision_readiness)
  ├─ Readiness Blockers: Critical open reviews > 0, Incomplete compliance, Stale score/risk
  └─ Advisory Warnings: High/Critical risk level, AI concerns, Mandatory/Critical failures
        ↓
Human Procurement Officer Decision Workspace
  ├─ Final Decision Action: QUALIFIED / DISQUALIFIED / UNDER_REVIEW
  ├─ Categorical Disqualification Reason (if DISQUALIFIED)
  ├─ Decision Summary & Mandatory Audit Justification (10 - 2000 chars)
  └─ Decision Readiness & Blocker Telemetry Banner
        ↓
POST /api/v1/procurement/tenders/{tender_id}/bids/{bid_id}/decision
        ↓
Atomic Versioning & Audit Recording:
  ├─ Enforce Decision Readiness (HTTP 400 Bad Request on blocked qualification)
  ├─ Link Active Evaluation Snapshot References (score_snapshot_id, risk_snapshot_id, ai_rec_id)
  ├─ Increment Decision Version (decision_version = max_version + 1)
  ├─ Supersede Prior Decisions (prior.is_current = False, prior.superseded_at = now)
  └─ Log Authoritative Decision Audit Trail
```

### Key Capabilities & Architectural Principles:
1. **Decision Readiness & Platform Safeguards**:
   - Evaluates whether a proposal is ready for qualification. Qualification is strictly blocked if unresolved critical review items exist, if compliance evaluation is incomplete, or if deterministic scores/risks are stale.
   - Procurement Officers can still disqualify defective bids or defer under review even if evaluation is incomplete.
2. **Decision Versioning & Superseding**:
   - Every updated decision is assigned an atomically incremented `decision_version`.
   - Exactly one decision per proposal is current (`is_current = True`). Prior decisions are marked `is_current = False` and preserve `superseded_at` timestamps and superseding decision IDs.
3. **Evaluation Snapshot Reference & Traceability**:
   - Each decision captures foreign-key references to the exact `score_snapshot_id`, `risk_snapshot_id`, and `ai_recommendation_id` active at decision time.
4. **Staleness Tracking on Upstream Changes**:
   - When upstream compliance results or human reviews mutate, current decisions are marked `is_stale = True` with an explainable audit reason, without automated decision reversals.
5. **Dashboard & Comparison Integration**:
   - `human_decision_status` is returned in tender evaluation listings (`/procurement/tenders/[id]/evaluation`) and comparative evaluation matrices (`/procurement/tenders/[id]/compare`).
6. **Multi-Tenant RBAC Security**:
   - Procurement Officers can only record decisions for tenders belonging to their organization (`organization_id`).
   - Cross-tenant officers receive `HTTP 404/403`. Bidders are strictly forbidden (`HTTP 403 Forbidden`).

### Master QA Suite Execution
```powershell
cd backend
venv\Scripts\activate
python scripts/test_part8d_final_decision.py
```
> **Result**: `ALL 38/38 PART 8D MASTER FINAL HUMAN DECISION TESTS PASSED (100% SUCCESS)`
