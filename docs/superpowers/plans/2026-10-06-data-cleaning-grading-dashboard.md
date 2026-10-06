# Data Cleaning Grading Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a zero-installation, projector-friendly standalone web dashboard (`challenge/grading_dashboard.html`) to grade student data cleaning CSV submissions against 12 challenge ground truth sets, featuring cell-by-cell visual diffs, official 18-point rubric grading, and interactive reveal cards showing explanations from the official answer keys.

**Architecture:** A standalone single-file HTML/JS application powered by Tailwind CSS and PapaParse. Ground truth datasets and 18-point rubrics for all 12 challenges are extracted from `groundtruth/` and `info/` and pre-bundled into a clean JavaScript registry. The client-side Diff Engine aligns rows by Primary Key, evaluates both overall cell accuracy and the official 18 checkpoints, and renders an interactive presentation grid with click-to-reveal explanation cards.

**Tech Stack:** HTML5, JavaScript (ES6+), Tailwind CSS, PapaParse (in-browser CSV parsing), Python 3 (for compiling the 12-set registry).

**Spec:** `docs/superpowers/specs/2026-10-06-data-cleaning-grading-dashboard-design.md`

## Global Constraints
- Target platform: Any standard web browser (Chrome, Safari, Edge) without requiring a backend server.
- Must run completely offline without internet dependencies once opened.
- Must support all 12 datasets (`set01` to `set12`) with auto-detection and manual dropdown selection.
- Must support the official 18-point rubric checklist with star `★` points per dataset.
- Must align rows by dataset Primary Key to avoid cascading row-offset errors.

## Review Focus
1. Extra duplicate rows in student files (e.g. unremoved SP-0110 duplicate or SP-0109 stock 18): must be flagged explicitly as extra rows without corrupting alignment of other rows.
2. Shuffled or re-ordered rows by students: must be correctly matched by Primary Key and graded green.
3. Formatted numbers vs raw numbers (e.g. `10` vs `10.0`, `1,000` vs `1000`): must normalize numerical equivalents correctly.
4. Thai language encodings (UTF-8 with and without BOM): PapaParse must parse cleanly without garbling Thai characters.
5. Missing values / empty strings: must match empty string or flagged accurately against Ground Truth.

---

### Task 1: Compile the 12-Dataset Registry & Rubrics Generator

**Files:**
- Create: `challenge/build_registry.py`
- Produces: `challenge/datasets_registry.json` and `challenge/datasets_registry.js`
- Test: `challenge/test_registry.py`

**Interfaces:**
- Produces: `window.DATASETS_REGISTRY` object mapping dataset keys (`set01`..`set12`) to metadata:
  ```json
  {
    "id": "set06",
    "name": "สต็อกอะไหล่",
    "filenamePattern": "set06|spareparts",
    "pkCol": "รหัสอะไหล่",
    "headers": ["รหัสอะไหล่", "ชื่ออะไหล่", "หมวด", "คงเหลือ", "หน่วย", "จุดสั่งซื้อ", "ที่เก็บ"],
    "groundTruthRows": [ ... 18 rows ... ],
    "rubric": [ ... 18 items with {#, level, origRow, col, origVal, correctVal, askOwner, explanation} ... ]
  }
  ```

- [ ] **Step 1: Write test for registry validation**
Create `challenge/test_registry.py` asserting that `datasets_registry.json` contains exactly 12 datasets, each having 18 ground truth rows and 18 rubric checkpoints with required keys.

- [ ] **Step 2: Run test to verify it fails**
Run: `python3 challenge/test_registry.py`
Expected: FAIL (file does not exist).

- [ ] **Step 3: Implement `challenge/build_registry.py`**
Parse all 12 CSVs in `groundtruth/` and all 12 tables in `info/ใบเฉลย-12ชุด-แจกหลังจบรอบ.docx`, compile into `challenge/datasets_registry.json` and export `challenge/datasets_registry.js`.

- [ ] **Step 4: Run build script and verify test passes**
Run: `python3 challenge/build_registry.py && python3 challenge/test_registry.py`
Expected: PASS (all 12 datasets valid).

---

### Task 2: Implement the Diff & Evaluation Engine

**Files:**
- Create: `challenge/diff_engine.js`
- Test: `challenge/test_engine.py` (via Node.js or Python CLI harness running test cases)

**Interfaces:**
- Function: `evaluateStudentData(studentRows, datasetConfig)`
  - Input: `studentRows` (Array of objects), `datasetConfig` (Registry entry)
  - Output:
    ```javascript
    {
      totalCells: Number,
      correctCells: Number,
      accuracyPct: Number,
      rubricScore: Number,       // 0-18
      rubricMax: 18,
      starScore: Number,         // 0-N
      starMax: Number,
      rubricResults: Array,      // 18 items with { item, passed, studentVal }
      matchedRows: Array,        // Table rows with cell-level status { val, status, gtVal, explanation, rubricRef }
      extraRows: Array,
      missingRows: Array
    }
    ```

- [ ] **Step 1: Write tests for the diff engine in `challenge/test_engine.py`**
Test cases:
1. `set06_spareparts.csv` (raw dirty) -> Expect rubric score 0/18.
2. `set06_spareparts_cleaned_v2.csv` (ground truth) -> Expect rubric score 18/18, cell accuracy 100%.
3. Re-ordered ground truth rows -> Expect rubric score 18/18 (proves PK alignment).

- [ ] **Step 2: Run test to verify it fails**
Run: `python3 challenge/test_engine.py`
Expected: FAIL (engine not implemented).

- [ ] **Step 3: Implement `challenge/diff_engine.js`**
Implement PK row alignment, extra/missing row handling, cell equivalence normalization, and 18-point rubric evaluation logic.

- [ ] **Step 4: Run test to verify it passes**
Run: `python3 challenge/test_engine.py`
Expected: PASS.

---

### Task 3: Build the Single-File Grading Dashboard UI

**Files:**
- Create: `challenge/grading_dashboard.html`

**Features & Layout:**
- Self-contained HTML embedding Tailwind CSS and PapaParse.
- Top control bar:
  - Dataset selector (12 sets) + Auto-detect indicator badge.
  - Large drag-and-drop CSV upload zone with file preview.
  - Controls: Presentation Mode toggle (Large Font / Normal), Reveal All / Hide All answers button.
- Score Dashboard:
  - Score card (`/ 18 คะแนน` with difficulty breakdown).
  - Star card (`★ / N ข้อดาว` for stakeholder interview questions).
  - Cell Accuracy percentage badge (`%`).
- Collapsible 18-Checkpoints Drawer:
  - Shows each of the 18 rubric criteria, pass/fail status, and difficulty tag.
- Interactive Large-Screen Table:
  - Aligned rows with clear primary key column.
  - Green cells for pass.
  - Red cells for fail.
  - Click-to-reveal modal/card on red cells: shows student value vs ground truth value, checkpoint difficulty badge, and exact tip from the official answer key.
  - Distinct warning banners for extra rows (e.g. unremoved duplicates) and missing rows.

- [ ] **Step 1: Create `challenge/grading_dashboard.html` integrating the UI, registry, and diff engine**
- [ ] **Step 2: Add presentation styles, responsive typography, and click-to-reveal interactions**
- [ ] **Step 3: Verify the dashboard works offline and in standalone browser mode**

---

### Task 4: End-to-End Verification & Demonstration

**Files:**
- Test script: `challenge/verify_e2e.py`

- [ ] **Step 1: Run comprehensive end-to-end verification script**
Test uploading `set06_spareparts.csv` and `set06_spareparts_cleaned.csv` into the dashboard logic and verify all DOM/output metrics.
- [ ] **Step 2: Validate across other sets (e.g. `set01`, `set02`) to ensure 12-set interoperability**
- [ ] **Step 3: Provide clear instructions and launch link for the instructor**
