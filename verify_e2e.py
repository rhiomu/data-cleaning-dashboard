#!/usr/bin/env python3
"""
verify_e2e.py - Comprehensive End-to-End Verification Suite for
Data Cleaning Challenge Grading Dashboard.

Verifies:
1. Raw dirty file (set06_spareparts.csv) -> confirms 0/18 rubric, 0/5 stars, extra rows detected.
2. Cleaned files (set06_spareparts_cleaned.csv & set06_spareparts_cleaned_v2.csv) ->
   confirms 18/18 rubric, 5/5 stars, 100% accuracy, 0 extra, 0 missing.
3. Cross-evaluating all 12 dataset ground truths from groundtruth/ directory ->
   confirms 12-set interoperability, auto-detection (by filename & by headers), 18/18 rubric, 5/5 stars, 100% accuracy.
4. Zero-dependency embedded CSV parser (DiffEngine.parseCsv) ->
   confirms 100% offline parsing capability yielding identical evaluation results.
5. Dashboard HTML integrity & projector mode ->
   confirms HTML structure, stylesheets, scripts, DOM controls, cards, drawer, modal, and projector mode styles.
6. DOM state simulation in Node.js ->
   confirms full user interaction flow (load dirty demo, load clean demo, toggle projector mode, reveal all, reset).
7. Robustness & fault tolerance ->
   confirms primary key alignment under row re-ordering, extra row injection, missing row omission, and normalization.

Exit Code: 0 on all tests passing.
"""

import os
import sys
import csv
import json
import re
import subprocess
import glob

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REGISTRY_JSON = os.path.join(BASE_DIR, 'datasets_registry.json')
REGISTRY_JS = os.path.join(BASE_DIR, 'datasets_registry.js')
DIFF_ENGINE_JS = os.path.join(BASE_DIR, 'diff_engine.js')
HTML_PATH = os.path.join(BASE_DIR, 'grading_dashboard.html')
GROUNDTRUTH_DIR = os.path.join(BASE_DIR, 'groundtruth')
RAW_SET06_CSV = os.path.join(BASE_DIR, 'set06_spareparts.csv')
CLEAN_SET06_V1_CSV = os.path.join(BASE_DIR, 'set06_spareparts_cleaned.csv')
CLEAN_SET06_V2_CSV = os.path.join(BASE_DIR, 'set06_spareparts_cleaned_v2.csv')


def print_header(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_step(step_num, title):
    print(f"\n[Test Step {step_num}] {title}")


def run_node(script_body):
    """Executes a Node.js script string and returns the stdout text."""
    proc = subprocess.run(
        ['node', '-e', script_body],
        capture_output=True,
        text=True,
        cwd=BASE_DIR
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Node execution failed with code {proc.returncode}:\nSTDERR:\n{proc.stderr}\nSTDOUT:\n{proc.stdout}")
    return proc.stdout.strip()


def load_csv_rows(filepath):
    """Loads CSV rows as dicts handling UTF-8 with BOM."""
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        return [dict(r) for r in reader]


def run_diff_engine_eval(student_rows, dataset_config):
    """Runs DiffEngine.evaluateStudentData via Node.js."""
    script = f"""
    const DiffEngine = require({json.dumps(DIFF_ENGINE_JS)});
    const studentRows = {json.dumps(student_rows, ensure_ascii=False)};
    const datasetConfig = {json.dumps(dataset_config, ensure_ascii=False)};
    const result = DiffEngine.evaluateStudentData(studentRows, datasetConfig);
    console.log(JSON.stringify(result));
    """
    out = run_node(script)
    return json.loads(out)


# ==============================================================================
# TEST 1: RAW DIRTY FILE EVALUATION (set06_spareparts.csv)
# ==============================================================================
def test_raw_dirty_file():
    print_step(1, "Evaluating raw dirty file: set06_spareparts.csv")

    assert os.path.exists(RAW_SET06_CSV), f"Missing {RAW_SET06_CSV}"
    with open(REGISTRY_JSON, 'r', encoding='utf-8') as f:
        registry = json.load(f)
    set06_cfg = registry['set06']

    raw_rows = load_csv_rows(RAW_SET06_CSV)
    print(f"  Loaded raw rows count: {len(raw_rows)}")
    assert len(raw_rows) == 20, f"Expected 20 rows in raw file, got {len(raw_rows)}"

    res = run_diff_engine_eval(raw_rows, set06_cfg)

    print(f"  -> Rubric Score:  {res['rubricScore']}/{res['rubricMax']}")
    print(f"  -> Star Score:    {res['starScore']}/{res['starMax']}")
    print(f"  -> Cell Accuracy: {res['accuracyPct']}% ({res['correctCells']}/{res['totalCells']} cells)")
    print(f"  -> Extra Rows:    {len(res['extraRows'])} detected")
    print(f"  -> Missing Rows:  {len(res['missingRows'])} detected")

    # Assertions
    assert res['rubricScore'] == 0, f"Expected rubricScore 0 on dirty file, got {res['rubricScore']}"
    assert res['rubricMax'] == 18, f"Expected rubricMax 18, got {res['rubricMax']}"
    assert res['starScore'] == 0, f"Expected starScore 0 on dirty file, got {res['starScore']}"
    assert res['starMax'] == 5, f"Expected starMax 5, got {res['starMax']}"
    assert len(res['rubricResults']) == 18, f"Expected 18 rubricResults, got {len(res['rubricResults'])}"

    # All 18 checkpoints must be failed
    failing_items = [r for r in res['rubricResults'] if not r['passed']]
    assert len(failing_items) == 18, f"Expected all 18 checkpoints to fail, but {len(res['rubricResults']) - len(failing_items)} passed"

    # Extra rows should catch the 2 duplicates (SP-0110 duplicate and SP-0109 duplicate)
    assert len(res['extraRows']) == 2, f"Expected 2 extra rows in dirty file, got {len(res['extraRows'])}"
    extra_pks = [r['pk'] for r in res['extraRows']]
    assert 'SP-0110' in extra_pks, f"SP-0110 duplicate missing from extraRows: {extra_pks}"
    assert 'SP-0109' in extra_pks, f"SP-0109 duplicate missing from extraRows: {extra_pks}"

    print("  -> PASS: Raw dirty file confirmed: 0/18 rubric, 0/5 stars, 2 extra duplicate rows flagged.")


# ==============================================================================
# TEST 2: CLEANED FILES EVALUATION (v1 & v2)
# ==============================================================================
def test_cleaned_files():
    print_step(2, "Evaluating cleaned files: set06_spareparts_cleaned.csv & set06_spareparts_cleaned_v2.csv")

    with open(REGISTRY_JSON, 'r', encoding='utf-8') as f:
        registry = json.load(f)
    set06_cfg = registry['set06']

    for label, filepath in [("Cleaned v1", CLEAN_SET06_V1_CSV), ("Cleaned v2", CLEAN_SET06_V2_CSV)]:
        print(f"\n  Testing {label} ({os.path.basename(filepath)})...")
        assert os.path.exists(filepath), f"File {filepath} not found"

        clean_rows = load_csv_rows(filepath)
        assert len(clean_rows) == 18, f"Expected 18 rows in clean file, got {len(clean_rows)}"

        res = run_diff_engine_eval(clean_rows, set06_cfg)
        print(f"    Rubric Score:  {res['rubricScore']}/{res['rubricMax']}")
        print(f"    Star Score:    {res['starScore']}/{res['starMax']}")
        print(f"    Cell Accuracy: {res['accuracyPct']}% ({res['correctCells']}/{res['totalCells']} cells)")
        print(f"    Extra Rows:    {len(res['extraRows'])}")
        print(f"    Missing Rows:  {len(res['missingRows'])}")

        assert res['rubricScore'] == 18, f"[{label}] Expected rubricScore 18, got {res['rubricScore']}"
        assert res['rubricMax'] == 18, f"[{label}] Expected rubricMax 18, got {res['rubricMax']}"
        assert res['starScore'] == 5, f"[{label}] Expected starScore 5, got {res['starScore']}"
        assert res['starMax'] == 5, f"[{label}] Expected starMax 5, got {res['starMax']}"
        assert res['accuracyPct'] == 100.0, f"[{label}] Expected 100% accuracy, got {res['accuracyPct']}%"
        assert res['correctCells'] == 126 and res['totalCells'] == 126, f"[{label}] Expected 126/126 cells, got {res['correctCells']}/{res['totalCells']}"
        assert len(res['extraRows']) == 0, f"[{label}] Expected 0 extra rows, got {len(res['extraRows'])}"
        assert len(res['missingRows']) == 0, f"[{label}] Expected 0 missing rows, got {len(res['missingRows'])}"

        # Every checkpoint must pass
        assert all(r['passed'] for r in res['rubricResults']), f"[{label}] Not all 18 checkpoints passed"
        star_results = [r for r in res['rubricResults'] if r['item']['askOwner']]
        assert len(star_results) == 5, f"[{label}] Expected 5 star checkpoints, got {len(star_results)}"
        assert all(r['passed'] for r in star_results), f"[{label}] Not all 5 star checkpoints passed"

        print(f"    -> PASS: {label} scored perfect 18/18, 5/5 stars, 100% cell accuracy (126/126).")


# ==============================================================================
# TEST 3: CROSS-EVALUATION OF ALL 12 GROUND TRUTH DATASETS
# ==============================================================================
def test_all_12_datasets_groundtruth():
    print_step(3, "Cross-evaluating all 12 dataset ground truths from groundtruth/ directory")

    with open(REGISTRY_JSON, 'r', encoding='utf-8') as f:
        registry = json.load(f)

    gt_files = sorted(glob.glob(os.path.join(GROUNDTRUTH_DIR, "set*.csv")))
    assert len(gt_files) == 12, f"Expected 12 ground truth CSV files in {GROUNDTRUTH_DIR}, found {len(gt_files)}"

    for gt_path in gt_files:
        fname = os.path.basename(gt_path)
        set_id = fname.split('_')[0]
        assert set_id in registry, f"Dataset id {set_id} not found in registry"

        cfg = registry[set_id]
        rows = load_csv_rows(gt_path)
        headers = list(rows[0].keys()) if rows else []

        # 1. Test auto-detection logic for this dataset
        detect_script = f"""
        const DATASETS_REGISTRY = require({json.dumps(REGISTRY_JSON)});
        const filename = {json.dumps(fname)};
        const headers = {json.dumps(headers, ensure_ascii=False)};
        
        function detect(fn, hdrs) {{
          const lowerName = (fn || '').toLowerCase();
          for (const [id, config] of Object.entries(DATASETS_REGISTRY)) {{
            if (config.filenamePattern && new RegExp(config.filenamePattern, 'i').test(lowerName)) return id;
            if (lowerName.includes(id)) return id;
          }}
          let bestId = null, bestOverlap = 0;
          for (const [id, config] of Object.entries(DATASETS_REGISTRY)) {{
            const overlap = (hdrs || []).filter(h => config.headers.includes(h)).length;
            if (overlap > bestOverlap && overlap >= 3) {{
              bestOverlap = overlap;
              bestId = id;
            }}
          }}
          return bestId;
        }}

        const byFile = detect(filename, []);
        const byHeader = detect('unknown.csv', headers);
        console.log(JSON.stringify({{ byFile, byHeader }}));
        """
        detect_res = json.loads(run_node(detect_script))
        assert detect_res['byFile'] == set_id, f"Auto-detection by filename failed for {fname}: got {detect_res['byFile']}"
        assert detect_res['byHeader'] == set_id, f"Auto-detection by headers failed for {fname}: got {detect_res['byHeader']}"

        # 2. Evaluate dataset
        res = run_diff_engine_eval(rows, cfg)
        expected_cells = len(rows) * len(cfg['headers'])

        assert res['rubricScore'] == 18, f"[{set_id}] Expected 18/18 rubric, got {res['rubricScore']}"
        assert res['starScore'] == 5, f"[{set_id}] Expected 5/5 stars, got {res['starScore']}"
        assert res['accuracyPct'] == 100.0, f"[{set_id}] Expected 100% accuracy, got {res['accuracyPct']}%"
        assert res['correctCells'] == expected_cells, f"[{set_id}] Cell count mismatch: {res['correctCells']} vs {expected_cells}"
        assert len(res['extraRows']) == 0, f"[{set_id}] Extra rows detected: {len(res['extraRows'])}"
        assert len(res['missingRows']) == 0, f"[{set_id}] Missing rows detected: {len(res['missingRows'])}"

        # Verify all checkpoints contain valid explanations
        for item in res['rubricResults']:
            assert item['passed'] is True, f"[{set_id}] Checkpoint #{item['item']['#']} failed"
            assert 'explanation' in item['item'] and len(item['item']['explanation']) > 0, f"[{set_id}] Missing explanation on #{item['item']['#']}"

        print(f"  -> PASS: {set_id} ({cfg['name']}): 18/18 rubric, 5/5 stars, 100% accuracy ({expected_cells}/{expected_cells} cells), auto-detected OK.")


# ==============================================================================
# TEST 4: ZERO-DEPENDENCY EMBEDDED CSV PARSER (DiffEngine.parseCsv)
# ==============================================================================
def test_embedded_csv_parser():
    print_step(4, "Testing zero-dependency embedded CSV parser (DiffEngine.parseCsv)")

    with open(REGISTRY_JSON, 'r', encoding='utf-8') as f:
        registry = json.load(f)
    set06_cfg = registry['set06']

    # Read raw text of dirty file
    with open(RAW_SET06_CSV, 'r', encoding='utf-8-sig') as f:
        raw_csv_text = f.read()

    # Read raw text of clean file
    with open(CLEAN_SET06_V2_CSV, 'r', encoding='utf-8-sig') as f:
        clean_csv_text = f.read()

    parse_script = f"""
    const DiffEngine = require({json.dumps(DIFF_ENGINE_JS)});
    const set06Cfg = {json.dumps(set06_cfg, ensure_ascii=False)};
    const rawText = {json.dumps(raw_csv_text)};
    const cleanText = {json.dumps(clean_csv_text)};

    const parsedRaw = DiffEngine.parseCsv(rawText);
    const parsedClean = DiffEngine.parseCsv(cleanText);

    const evalRaw = DiffEngine.evaluateStudentData(parsedRaw, set06Cfg);
    const evalClean = DiffEngine.evaluateStudentData(parsedClean, set06Cfg);

    console.log(JSON.stringify({{
      rawRowCount: parsedRaw.length,
      cleanRowCount: parsedClean.length,
      rawScore: evalRaw.rubricScore,
      cleanScore: evalClean.rubricScore,
      cleanAcc: evalClean.accuracyPct,
      cleanStars: evalClean.starScore
    }}));
    """
    res = json.loads(run_node(parse_script))

    assert res['rawRowCount'] == 20, f"DiffEngine.parseCsv parsed {res['rawRowCount']} raw rows, expected 20"
    assert res['cleanRowCount'] == 18, f"DiffEngine.parseCsv parsed {res['cleanRowCount']} clean rows, expected 18"
    assert res['rawScore'] == 0, f"Parsed raw score was {res['rawScore']}, expected 0"
    assert res['cleanScore'] == 18, f"Parsed clean score was {res['cleanScore']}, expected 18"
    assert res['cleanAcc'] == 100.0, f"Parsed clean accuracy was {res['cleanAcc']}, expected 100.0"
    assert res['cleanStars'] == 5, f"Parsed clean stars was {res['cleanStars']}, expected 5"

    print("  -> PASS: DiffEngine.parseCsv functions seamlessly with zero external dependencies (20 raw rows -> 0/18; 18 clean rows -> 18/18, 100%).")


# ==============================================================================
# TEST 5: DASHBOARD HTML INTEGRITY & PROJECTOR MODE VALIDATION
# ==============================================================================
def test_dashboard_html_integrity():
    print_step(5, "Validating dashboard HTML structure, scripts, and projector styles")

    assert os.path.exists(HTML_PATH), f"Missing {HTML_PATH}"
    with open(HTML_PATH, 'r', encoding='utf-8') as f:
        html = f.read()

    # 1. Check relative script links
    assert '<script src="datasets_registry.js"></script>' in html, "HTML missing datasets_registry.js link"
    assert '<script src="diff_engine.js"></script>' in html, "HTML missing diff_engine.js link"

    # 2. Check offline fallback scripts and fonts
    assert 'tailwindcss' in html, "HTML missing Tailwind CSS reference"
    assert 'papaparse' in html, "HTML missing PapaParse reference"
    assert 'Prompt' in html and 'Sarabun' in html, "HTML missing Thai typography fonts"

    # 3. Check Projector Mode styles
    assert 'body.projector-mode' in html, "HTML missing body.projector-mode CSS rule"
    assert 'projector-card' in html, "HTML missing projector-card styling"
    assert '.cell-fail' in html and '.cell-pass' in html, "HTML missing cell diff styling"

    # 4. Check all key interactive IDs
    required_ids = [
        'projectorModeToggle',
        'revealAllToggle',
        'datasetSelect',
        'autoDetectBadge',
        'loadDirtyDemoBtn',
        'loadCleanDemoBtn',
        'resetDataBtn',
        'dropzone',
        'fileInput',
        'fileLoadedBanner',
        'scoreDashboard',
        'rubricScoreDisplay',
        'starScoreDisplay',
        'accuracyDisplay',
        'rowCountDisplay',
        'columnAccuracyContainer',
        'toggleCheckpointsBtn',
        'checkpointsList',
        'diffTable',
        'tableHeadRow',
        'tableBody',
        'extraRowsBanner',
        'missingRowsBanner',
        'explanationModal',
        'modalStudentVal',
        'modalGtVal',
        'modalExplanation',
    ]
    for rid in required_ids:
        assert f'id="{rid}"' in html, f"Missing required element id='{rid}' in HTML"

    # 5. Check all 12 dataset dropdown options
    for i in range(1, 13):
        sid = f'set{i:02d}'
        assert f'value="{sid}"' in html, f"Missing option value='{sid}' in datasetSelect"

    print(f"  -> PASS: HTML integrity verified ({len(html):,} bytes, all scripts, {len(required_ids)} DOM IDs, and all 12 sets present).")


# ==============================================================================
# TEST 6: FULL DOM STATE SIMULATION IN NODE.JS RUNTIME
# ==============================================================================
def test_dom_simulation():
    print_step(6, "Simulating full DOM interaction flow in Node.js runtime")

    with open(HTML_PATH, 'r', encoding='utf-8') as f:
        html = f.read()

    # Extract inline javascript
    script_matches = re.findall(r'<script>(.*?)</script>', html, re.DOTALL)
    assert len(script_matches) > 0, "No inline script found in HTML"
    inline_js = script_matches[-1]

    sim_script = f"""
    const DiffEngine = require({json.dumps(DIFF_ENGINE_JS)});
    const DATASETS_REGISTRY = require({json.dumps(REGISTRY_JSON)});

    const windowListeners = {{}};
    const domRegistry = {{}};

    function createMockEl(tag = 'div', id = '') {{
      return {{
        tagName: tag.toUpperCase(),
        id: id || '',
        classList: {{
          _set: new Set(),
          add(c) {{ this._set.add(c); }},
          remove(c) {{ this._set.delete(c); }},
          toggle(c, f) {{ if (f !== undefined) {{ if (f) this._set.add(c); else this._set.delete(c); }} else {{ if (this._set.has(c)) this._set.delete(c); else this._set.add(c); }} }},
          contains(c) {{ return this._set.has(c); }}
        }},
        style: {{}},
        attributes: {{}},
        children: [],
        listeners: {{}},
        appendChild(child) {{ this.children.push(child); }},
        addEventListener(evt, fn) {{ this.listeners[evt] = this.listeners[evt] || []; this.listeners[evt].push(fn); }},
        querySelectorAll(sel) {{ return []; }},
        trigger(evt, data) {{ if (this.listeners[evt]) this.listeners[evt].forEach(fn => fn(data || {{ target: this }})); }},
        setAttribute(k, v) {{ this.attributes[k] = v; }},
        getAttribute(k) {{ return this.attributes[k] || ''; }}
      }};
    }}

    function getEl(id) {{
      if (!domRegistry[id]) {{
        domRegistry[id] = createMockEl('div', id);
      }}
      return domRegistry[id];
    }}

    const bodyEl = getEl('body');

    global.window = {{
      DATASETS_REGISTRY,
      DiffEngine,
      addEventListener: (evt, fn) => {{
        windowListeners[evt] = windowListeners[evt] || [];
        windowListeners[evt].push(fn);
      }},
    }};

    global.document = {{
      getElementById: (id) => getEl(id),
      createElement: (tag) => createMockEl(tag),
      querySelectorAll: () => [],
      addEventListener: () => {{}},
      body: bodyEl
    }};

    // Execute inline dashboard code
    {inline_js}

    // Fire DOMContentLoaded to bootstrap dashboard
    if (windowListeners['DOMContentLoaded']) {{
      windowListeners['DOMContentLoaded'].forEach(fn => fn());
    }}

    // --- Scenario A: After Bootstrap or Trigger Load Dirty Demo Button ---
    const loadDirtyBtn = getEl('loadDirtyDemoBtn');
    loadDirtyBtn.trigger('click');

    const dirtyRubricScore = getEl('rubricScoreDisplay').textContent.trim();
    const dirtyStarScore = getEl('starScoreDisplay').textContent.trim();
    const dirtyAccuracy = getEl('accuracyDisplay').textContent.trim();
    const extraRowsBannerVisible = !getEl('extraRowsBanner').classList.contains('hidden');

    // --- Scenario B: Trigger Load Clean Demo Button ---
    const loadCleanBtn = getEl('loadCleanDemoBtn');
    loadCleanBtn.trigger('click');

    const cleanRubricScore = getEl('rubricScoreDisplay').textContent.trim();
    const cleanStarScore = getEl('starScoreDisplay').textContent.trim();
    const cleanAccuracy = getEl('accuracyDisplay').textContent.trim();
    const cleanRowCount = getEl('rowCountDisplay').textContent.trim();
    const extraRowsBannerHidden = getEl('extraRowsBanner').classList.contains('hidden');

    // --- Scenario C: Toggle Projector Mode ---
    const projToggle = getEl('projectorModeToggle');
    projToggle.trigger('click');
    const isProjActive = bodyEl.classList.contains('projector-mode');
    projToggle.trigger('click');
    const isProjDeactivated = !bodyEl.classList.contains('projector-mode');

    // --- Scenario D: Trigger Reset Button ---
    const resetBtn = getEl('resetDataBtn');
    resetBtn.trigger('click');
    const resetRubricScore = getEl('rubricScoreDisplay').textContent.trim();

    console.log(JSON.stringify({{
      dirtyRubricScore,
      dirtyStarScore,
      dirtyAccuracy,
      extraRowsBannerVisible,
      cleanRubricScore,
      cleanStarScore,
      cleanAccuracy,
      cleanRowCount,
      extraRowsBannerHidden,
      isProjActive,
      isProjDeactivated,
      resetRubricScore
    }}));
    """
    sim_res = json.loads(run_node(sim_script))

    # Assertions on Simulated User Actions
    assert sim_res['dirtyRubricScore'] == '0', f"Expected dirty rubric score 0, got {sim_res['dirtyRubricScore']}"
    assert sim_res['dirtyStarScore'] == '★ 0', f"Expected dirty star score '★ 0', got {sim_res['dirtyStarScore']}"
    assert sim_res['extraRowsBannerVisible'] is True, "Expected extra rows banner to be visible on dirty file"

    assert sim_res['cleanRubricScore'] == '18', f"Expected clean rubric score 18, got {sim_res['cleanRubricScore']}"
    assert sim_res['cleanStarScore'] == '★ 5', f"Expected clean star score '★ 5', got {sim_res['cleanStarScore']}"
    assert sim_res['cleanAccuracy'] == '100%', f"Expected clean accuracy '100%', got {sim_res['cleanAccuracy']}"
    assert sim_res['cleanRowCount'] == '18', f"Expected clean row count '18', got {sim_res['cleanRowCount']}"
    assert sim_res['extraRowsBannerHidden'] is True, "Expected extra rows banner to be hidden on clean file"

    assert sim_res['isProjActive'] is True, "Expected projector-mode class added to body"
    assert sim_res['isProjDeactivated'] is True, "Expected projector-mode class removed from body on toggle"
    assert sim_res['resetRubricScore'] == '--', "Expected rubric score reset to '--'"

    print("  -> PASS: Full DOM simulation verified (Dirty demo 0/18 -> Clean demo 18/18 -> Projector toggle -> Reset).")


# ==============================================================================
# TEST 7: RESILIENCE & EDGE CASE VERIFICATION
# ==============================================================================
def test_resilience_and_edge_cases():
    print_step(7, "Testing engine resilience (Row re-ordering, Extra injection, Missing omission, Normalization)")

    with open(REGISTRY_JSON, 'r', encoding='utf-8') as f:
        registry = json.load(f)
    set06_cfg = registry['set06']
    clean_rows = load_csv_rows(CLEAN_SET06_V2_CSV)

    # 1. Shuffled / Re-ordered rows
    reversed_rows = list(reversed(clean_rows))
    res_rev = run_diff_engine_eval(reversed_rows, set06_cfg)
    assert res_rev['rubricScore'] == 18, "Re-ordered rows failed 18/18 rubric"
    assert res_rev['accuracyPct'] == 100.0, "Re-ordered rows failed 100% accuracy"
    assert len(res_rev['extraRows']) == 0 and len(res_rev['missingRows']) == 0
    print("  -> Subtest 7.1: Row re-ordering handled smoothly via PK alignment (18/18, 100%).")

    # 2. Injected extra unexpected row
    extra_rows = clean_rows + [{"รหัสอะไหล่": "SP-9999", "ชื่ออะไหล่": "อะไหล่พิเศษ", "หมวด": "เครื่องกล", "คงเหลือ": "1", "หน่วย": "ชิ้น", "จุดสั่งซื้อ": "1", "ที่เก็บ": "A1"}]
    res_extra = run_diff_engine_eval(extra_rows, set06_cfg)
    assert len(res_extra['extraRows']) == 1, "Failed to detect injected extra row"
    assert res_extra['extraRows'][0]['pk'] == 'SP-9999'
    print("  -> Subtest 7.2: Injected extra row (SP-9999) correctly detected in extraRows.")

    # 3. Omitted missing row
    missing_rows = clean_rows[1:]  # Drop SP-0101
    res_missing = run_diff_engine_eval(missing_rows, set06_cfg)
    assert len(res_missing['missingRows']) == 1, "Failed to detect omitted missing row"
    assert res_missing['missingRows'][0]['pk'] == 'SP-0101'
    assert res_missing['rubricScore'] < 18, "Score should drop when row is omitted"
    print("  -> Subtest 7.3: Omitted row (SP-0101) correctly detected in missingRows.")

    # 4. Strict business case sensitivity vs number normalization
    mod_rows = [dict(r) for r in clean_rows]
    for r in mod_rows:
        if r['รหัสอะไหล่'] == 'SP-0114':
            r['ที่เก็บ'] = 'c1'  # lowercase c1 instead of C1
    res_case = run_diff_engine_eval(mod_rows, set06_cfg)
    assert res_case['rubricScore'] == 17, f"Expected score 17 for lowercase c1, got {res_case['rubricScore']}"
    print("  -> Subtest 7.4: Domain rule preserved: case-sensitive location ('c1' vs 'C1') flagged.")


# ==============================================================================
# MAIN TEST HARNESS
# ==============================================================================
def main():
    print_header("E2E VERIFICATION: DATA CLEANING GRADING DASHBOARD")
    print(f"Working Directory: {BASE_DIR}")

    try:
        test_raw_dirty_file()
        test_cleaned_files()
        test_all_12_datasets_groundtruth()
        test_embedded_csv_parser()
        test_dashboard_html_integrity()
        test_dom_simulation()
        test_resilience_and_edge_cases()

        print_header("ALL END-TO-END VERIFICATION TESTS PASSED SUCCESSFULLY! (EXIT 0)")
        print("\nSummary:")
        print("  ✓ Step 1: Raw dirty set06 scored 0/18 rubric, 0/5 stars, 2 duplicates caught.")
        print("  ✓ Step 2: Cleaned set06 (v1 & v2) scored 18/18 rubric, 5/5 stars, 100% cell accuracy.")
        print("  ✓ Step 3: All 12 datasets in groundtruth/ cross-evaluated with 100% accuracy and auto-detection.")
        print("  ✓ Step 4: Zero-dependency embedded CSV parser verified offline.")
        print("  ✓ Step 5: Dashboard HTML structure, projector styles, and DOM IDs validated.")
        print("  ✓ Step 6: Full user interaction flow simulated in DOM runtime.")
        print("  ✓ Step 7: Resilience against re-ordering, extra/missing rows, and edge cases verified.")
        sys.exit(0)

    except Exception as e:
        print_header("VERIFICATION FAILED")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
