# High-Volume Bulk Verification & Batch Processing Guide (200 Bidders Flow)

This guide explains how to set up, run, and evaluate the **High-Volume Bulk Verification & Batch Processing Engine** in **BidVerify AI**.

---

## 🌟 Overview & Features

Instead of manually checking every bidder's credentials, tax certificates, financial turnover, and OEM declarations, a **Procurement Officer** can process hundreds of bidders or bid documents in a single unified operation (**"Verify All"**).

### 🔄 Multi-Stage Pipeline Flow
```text
200 Bidders Scope ──► Verify All (1-Click) ──► Stage 3: Document Processing (PDF Text & OCR)
                                                          │
Stage 5: Compliance & Results ◄── Stage 4: Verification ◄─┘
 (128 PASS, 47 REVIEW,          (GST / PAN / MCA / CVC)
  20 FAIL, 5 CRITICAL)
```

### 📊 Results Breakdown Example (200 Bidders Benchmark)
* 🟢 **128 PASS (64.0%)**: Fully compliant across statutory, financial, and technical rules.
* 🟡 **47 REVIEW REQUIRED (23.5%)**: Flagged for minor document ambiguity or officer sign-off.
* 🔴 **20 FAIL (10.0%)**: Non-compliant (e.g. turnover below mandatory threshold).
* 🚨 **5 CRITICAL (2.5%)**: Severe anomalies, debarment matches, or active CVC blacklisting.

---

## 🛠️ Step-by-Step Setup & Running Guide

### Step 1: Environment & Dependency Setup

#### Backend Setup:
```bash
cd backend
python -m pip install -r requirements.txt
```

#### Frontend Setup:
```bash
cd frontend
npm install
```

---

### Step 2: Database Initialization & Seeding 200-Bidder Tender

Run the automated database seeders from the `backend` directory:

1. **Seed System Roles & Test Users**:
   ```bash
   python scripts/seed_roles.py
   python scripts/create_test_users.py
   ```

2. **Seed 200-Bidder Benchmark Tender**:
   ```bash
   python scripts/seed_200_bidders_tender.py
   ```
   *Output will confirm*:
   ```text
   ================================================================================
   SUCCESS: 200-Bidder Bulk Verification Benchmark Tender Ready!
   Tender ID: <UUID>
   Tender Number: GEM/2026/B/200000
   Run Guide: Log in as 'procurement@test.local' / 'TestPassword123!' on Frontend
   ================================================================================
   ```

---

### Step 3: Launching the Applications

#### 1. Start FastAPI Backend (Port 8000)
From `backend` directory:
```bash
uvicorn app.main:app --reload --port 8000
```
*Backend API Docs will be live at*: `http://localhost:8000/docs`

#### 2. Start Next.js Frontend (Port 3000)
From `frontend` directory:
```bash
npm run dev
```
*Frontend Portal will be live at*: `http://localhost:3000`

---

### Step 4: Testing & Executing the 200-Bidder Flow on Frontend

1. **Log in to Procurement Portal**:
   - Open `http://localhost:3000/login`
   - **Email**: `procurement@test.local` (or `procurement.officer@railways.gov.in`)
   - **Password**: `TestPassword123!`

2. **Navigate to Batch Verification Center**:
   - Click on **Verifications & Batch Processing** on the side navigation (`/procurement/verifications`).
   - Or navigate to **Participating Bidders** (`/procurement/bidders`).

3. **Select Benchmark Tender**:
   - In the top dropdown, select: **`GEM/2026/B/200000 • GeM High-Volume Enterprise IT Procurement...`**

4. **Trigger Single-Operation Batch Processing ("Verify All")**:
   - Click the purple **"Verify All Bids"** button.
   - The **Bulk Verification & Batch Evaluation Modal** will launch.
   - Click **"Run Bulk Evaluation on All Bids"** (or inspect pre-calculated telemetry).

5. **Observe Real-Time Telemetry & Results Breakdown**:
   - **Stage Flow Visualizer**: `200 Bidders` → `Verify All` → `Doc Processing` → `Verification` → `Compliance & Results`.
   - **Live Progress Bar**: Shows execution percentage (0% to 100%).
   - **Summary Stat Cards**:
     - 🟢 **128 PASS**
     - 🟡 **47 REVIEW**
     - 🔴 **20 FAIL**
     - 🚨 **5 CRITICAL**
   - **Per-Bid Directory**: Search by bidder name/ID or filter by status (`CRITICAL`, `REVIEW_REQUIRED`, `FAILED`, `SUCCESS`).

---

## 🧪 Automated Verification & Test Commands

To run automated backend test suites for batch verification:

```bash
cd backend
python scripts/test_part9_bulk_evaluation.py
```

Or run with PyTest:
```bash
pytest tests/test_bulk_evaluation.py -v
```

---

## 📈 Key Benefits & Scalability Impact

1. **Massive Efficiency Gain**: Reduces processing time for 200 bidders from days of manual reading to seconds/minutes.
2. **Deterministic Rules & Anomaly Detection**: Automatically catches CVC blacklisting, GSTIN mismatches, and statutory defects.
3. **Failure Isolation**: Processing errors on individual corrupted files do not halt the overall batch.
