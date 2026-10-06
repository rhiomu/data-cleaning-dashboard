#!/usr/bin/env python3
"""
test_engine.py - Test suite for challenge/diff_engine.js

Tests the evaluation and diff engine against requirements:
1. Raw dirty file (set06_spareparts.csv) -> rubric score 0/18.
2. Ground truth clean file (set06_spareparts_cleaned_v2.csv) -> rubric score 18/18, accuracy 100%.
3. Re-ordered ground truth rows -> rubric score 18/18 (proves PK alignment).
4. Extra row detection -> detects unremoved / unexpected rows.
5. Missing row detection -> detects omitted rows.
6. Composite primary key alignment (set09_electricity).
7. Cell value normalization (whitespace, numeric equivalence, strict case).
"""

import os
import csv
import json
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIFF_ENGINE_JS = os.path.join(BASE_DIR, 'diff_engine.js')
REGISTRY_JSON = os.path.join(BASE_DIR, 'datasets_registry.json')
RAW_SET06_CSV = os.path.join(BASE_DIR, 'set06_spareparts.csv')
CLEAN_SET06_CSV = os.path.join(BASE_DIR, 'set06_spareparts_cleaned_v2.csv')


def load_csv_rows(csv_path):
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        return [dict(r) for r in reader]


def run_node_eval(student_rows, dataset_config):
    """
    Invokes node to execute evaluateStudentData from diff_engine.js
    """
    script = f"""
    const path = require('path');
    const {{ evaluateStudentData }} = require({json.dumps(DIFF_ENGINE_JS)});
    const studentRows = {json.dumps(student_rows, ensure_ascii=False)};
    const datasetConfig = {json.dumps(dataset_config, ensure_ascii=False)};
    
    const result = evaluateStudentData(studentRows, datasetConfig);
    console.log(JSON.stringify(result));
    """
    proc = subprocess.run(
        ['node', '-e', script],
        capture_output=True,
        text=True,
        cwd=BASE_DIR
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Node execution failed (code {proc.returncode}):\n{proc.stderr}\n{proc.stdout}")
    
    return json.loads(proc.stdout)


def main():
    print("==================================================")
    print("Running Diff Engine Test Suite (TDD)")
    print("==================================================")

    if not os.path.exists(DIFF_ENGINE_JS):
        print(f"FAIL: {DIFF_ENGINE_JS} does not exist yet (Expected in RED phase)")
        sys.exit(1)

    with open(REGISTRY_JSON, 'r', encoding='utf-8') as f:
        registry = json.load(f)

    set06_cfg = registry['set06']
    set09_cfg = registry['set09']

    # --- Test Case 1: Raw dirty file (set06_spareparts.csv) ---
    print("\n[Test 1] Testing raw dirty file: set06_spareparts.csv ...")
    raw_rows = load_csv_rows(RAW_SET06_CSV)
    res_raw = run_node_eval(raw_rows, set06_cfg)
    
    print(f"  Rubric Score: {res_raw['rubricScore']}/{res_raw['rubricMax']}")
    print(f"  Star Score:   {res_raw['starScore']}/{res_raw['starMax']}")
    print(f"  Accuracy:     {res_raw['accuracyPct']}% ({res_raw['correctCells']}/{res_raw['totalCells']})")
    print(f"  Extra rows:   {len(res_raw['extraRows'])}")

    assert res_raw['rubricScore'] == 0, f"Expected rubricScore 0/18 on dirty file, got {res_raw['rubricScore']}"
    assert res_raw['rubricMax'] == 18, f"Expected rubricMax 18, got {res_raw['rubricMax']}"
    assert res_raw['starScore'] == 0, f"Expected starScore 0/5 on dirty file, got {res_raw['starScore']}"
    assert res_raw['starMax'] == 5, f"Expected starMax 5, got {res_raw['starMax']}"
    assert len(res_raw['rubricResults']) == 18, f"Expected 18 rubricResults, got {len(res_raw['rubricResults'])}"
    assert all(r['passed'] is False for r in res_raw['rubricResults']), "All 18 checkpoints should be False on raw dirty file"
    assert len(res_raw['extraRows']) >= 1, "Expected extra rows detected for unremoved duplicates"
    print("  -> PASS: Raw dirty file scored 0/18 with all 18 checkpoints failing.")

    # --- Test Case 2: Clean ground truth file (set06_spareparts_cleaned_v2.csv) ---
    print("\n[Test 2] Testing cleaned ground truth: set06_spareparts_cleaned_v2.csv ...")
    clean_rows = load_csv_rows(CLEAN_SET06_CSV)
    res_clean = run_node_eval(clean_rows, set06_cfg)

    print(f"  Rubric Score: {res_clean['rubricScore']}/{res_clean['rubricMax']}")
    print(f"  Star Score:   {res_clean['starScore']}/{res_clean['starMax']}")
    print(f"  Accuracy:     {res_clean['accuracyPct']}% ({res_clean['correctCells']}/{res_clean['totalCells']})")
    print(f"  Extra rows:   {len(res_clean['extraRows'])}, Missing rows: {len(res_clean['missingRows'])}")

    assert res_clean['rubricScore'] == 18, f"Expected rubricScore 18/18 on clean file, got {res_clean['rubricScore']}"
    assert res_clean['starScore'] == 5, f"Expected starScore 5/5 on clean file, got {res_clean['starScore']}"
    assert res_clean['accuracyPct'] == 100.0, f"Expected 100% accuracy, got {res_clean['accuracyPct']}%"
    assert res_clean['correctCells'] == res_clean['totalCells'], "All cells should be correct"
    assert len(res_clean['extraRows']) == 0, "Expected 0 extra rows"
    assert len(res_clean['missingRows']) == 0, "Expected 0 missing rows"
    assert all(r['passed'] is True for r in res_clean['rubricResults']), "All 18 checkpoints should be True on clean file"
    print("  -> PASS: Clean ground truth file scored 18/18 (100% accuracy, 5/5 stars).")

    # --- Test Case 3: Re-ordered ground truth rows ---
    print("\n[Test 3] Testing re-ordered ground truth rows ...")
    reordered_rows = list(reversed(clean_rows))
    res_reordered = run_node_eval(reordered_rows, set06_cfg)

    print(f"  Rubric Score: {res_reordered['rubricScore']}/{res_reordered['rubricMax']}")
    print(f"  Accuracy:     {res_reordered['accuracyPct']}% ({res_reordered['correctCells']}/{res_reordered['totalCells']})")

    assert res_reordered['rubricScore'] == 18, f"Expected rubricScore 18/18 on re-ordered clean rows, got {res_reordered['rubricScore']}"
    assert res_reordered['accuracyPct'] == 100.0, f"Expected 100% accuracy on re-ordered clean rows, got {res_reordered['accuracyPct']}%"
    assert len(res_reordered['extraRows']) == 0, "Expected 0 extra rows"
    assert len(res_reordered['missingRows']) == 0, "Expected 0 missing rows"
    print("  -> PASS: Re-ordered ground truth matched perfectly via PK alignment (18/18, 100%).")

    # --- Test Case 4: Extra row detection ---
    print("\n[Test 4] Testing extra row detection ...")
    rows_with_extra = clean_rows + [{"รหัสอะไหล่": "SP-9999", "ชื่ออะไหล่": "อะไหล่ส่วนเกิน", "หมวด": "เครื่องกล", "คงเหลือ": "5", "หน่วย": "ชิ้น", "จุดสั่งซื้อ": "1", "ที่เก็บ": "Z1"}]
    res_extra = run_node_eval(rows_with_extra, set06_cfg)
    assert len(res_extra['extraRows']) == 1, f"Expected 1 extra row, got {len(res_extra['extraRows'])}"
    assert res_extra['extraRows'][0]['pk'] == "SP-9999"
    print("  -> PASS: Successfully detected extra/unexpected row (SP-9999).")

    # --- Test Case 5: Missing row detection ---
    print("\n[Test 5] Testing missing row detection ...")
    rows_missing_one = clean_rows[1:] # Omit first row (SP-0101)
    res_missing = run_node_eval(rows_missing_one, set06_cfg)
    assert len(res_missing['missingRows']) == 1, f"Expected 1 missing row, got {len(res_missing['missingRows'])}"
    assert res_missing['missingRows'][0]['pk'] == "SP-0101"
    assert res_missing['rubricScore'] < 18, "Score should drop when a row is missing"
    print("  -> PASS: Successfully detected missing row (SP-0101).")

    # --- Test Case 6: Composite PK dataset (set09_electricity) ---
    print("\n[Test 6] Testing composite PK dataset (set09: เดือน + อาคาร) ...")
    gt_set09 = set09_cfg['groundTruthRows']
    res_set09 = run_node_eval(gt_set09, set09_cfg)
    assert res_set09['rubricScore'] == 18, f"Expected 18/18 for set09 GT, got {res_set09['rubricScore']}"
    assert res_set09['accuracyPct'] == 100.0, f"Expected 100% for set09 GT, got {res_set09['accuracyPct']}"
    print("  -> PASS: Successfully evaluated composite PK dataset (set09: 18/18, 100%).")

    # --- Test Case 7: Normalization checks ---
    print("\n[Test 7] Testing normalization (whitespace, numeric formatting, case sensitivity) ...")
    # Make modified clean rows with formatted number (1,000) and padded whitespace
    mod_clean_rows = [dict(r) for r in clean_rows]
    # In SP-0108, จุดสั่งซื้อ is "100" -> change to " 100 " and "100.0"
    for r in mod_clean_rows:
        if r['รหัสอะไหล่'] == 'SP-0108':
            r['จุดสั่งซื้อ'] = '  100.0  '
    res_norm = run_node_eval(mod_clean_rows, set06_cfg)
    assert res_norm['accuracyPct'] == 100.0, f"Expected 100% accuracy with whitespace and numeric equivalence, got {res_norm['accuracyPct']}"

    # Strict case sensitivity: change ที่เก็บ "C1" to "c1" in SP-0114
    for r in mod_clean_rows:
        if r['รหัสอะไหล่'] == 'SP-0114':
            r['ที่เก็บ'] = 'c1'
    res_case = run_node_eval(mod_clean_rows, set06_cfg)
    assert res_case['accuracyPct'] < 100.0, "Expected accuracy < 100% when case differs (c1 vs C1)"
    assert res_case['rubricScore'] == 17, f"Expected rubric score 17 when c1 is not capitalized, got {res_case['rubricScore']}"
    print("  -> PASS: Whitespace and numeric equivalence pass, case sensitivity preserved.")

    # --- Test Case 8: All 12 Challenge Sets Ground Truth Verification ---
    print("\n[Test 8] Testing all 12 datasets ground truth evaluation ...")
    for sid, cfg in registry.items():
        res = run_node_eval(cfg['groundTruthRows'], cfg)
        assert res['rubricScore'] == 18, f"Expected 18/18 for {sid}, got {res['rubricScore']}"
        assert res['starScore'] == 5, f"Expected 5/5 stars for {sid}, got {res['starScore']}"
        assert res['accuracyPct'] == 100.0, f"Expected 100% accuracy for {sid}, got {res['accuracyPct']}"
        assert len(res['extraRows']) == 0, f"Expected 0 extra rows for {sid}"
        assert len(res['missingRows']) == 0, f"Expected 0 missing rows for {sid}"
        print(f"  -> PASS: {sid} ({cfg['name']}): 18/18 rubric, 5/5 stars, 100% cell accuracy.")

    print("\n==================================================")
    print("ALL DIFF ENGINE TESTS PASSED SUCCESSFULLY! (GREEN)")
    print("==================================================")


if __name__ == '__main__':
    main()
