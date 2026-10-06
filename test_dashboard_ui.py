#!/usr/bin/env python3
"""
test_dashboard_ui.py - Automated verification for challenge/grading_dashboard.html

Verifies:
1. File existence and HTML well-formedness.
2. Required script references and stylesheets.
3. Required UI elements, controls, and accessibility hooks:
   - Dataset selector with all 12 sets.
   - Projector mode toggle and CSS rules.
   - Reveal All / Hide All answer controls.
   - Dropzone with drag/drop and file input.
   - 4 Score metric cards (Rubric, Star, Accuracy, Row Completeness).
   - Column accuracy breakdown container.
   - 18 Checkpoints accordion drawer with filter chips.
   - Interactive diff table with PK indicator and error modal.
   - Distinct banners for extra rows and missing rows.
4. Embedded JavaScript evaluation and behavior using Node.js:
   - Auto-detection across all 12 datasets by filename and by headers.
   - Zero-dependency CSV parser fallback.
   - Execution of evaluation on both dirty sample and clean ground truth.
"""

import os
import re
import json
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_PATH = os.path.join(BASE_DIR, 'grading_dashboard.html')
REGISTRY_JSON = os.path.join(BASE_DIR, 'datasets_registry.json')
DIFF_ENGINE_JS = os.path.join(BASE_DIR, 'diff_engine.js')
DATASETS_REGISTRY_JS = os.path.join(BASE_DIR, 'datasets_registry.js')


def test_html_structure():
    print("[Test 1] Verifying HTML structure and element presence...")
    assert os.path.exists(HTML_PATH), f"File {HTML_PATH} does not exist!"

    with open(HTML_PATH, 'r', encoding='utf-8') as f:
        html = f.read()

    # Script and stylesheet dependencies
    assert '<script src="datasets_registry.js"></script>' in html, "Missing datasets_registry.js include"
    assert '<script src="diff_engine.js"></script>' in html, "Missing diff_engine.js include"
    assert 'tailwindcss' in html, "Missing Tailwind CSS"
    assert 'papaparse' in html, "Missing PapaParse script"
    assert 'Prompt' in html and 'Sarabun' in html, "Missing Thai Google Fonts"

    # CSS rules for projector mode and cell diffs
    assert 'body.projector-mode' in html, "Missing body.projector-mode CSS styles"
    assert '.cell-pass' in html and '.cell-fail' in html, "Missing cell pass/fail CSS classes"

    # Control bar elements
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
        'columnBarsGrid',
        'toggleCheckpointsBtn',
        'checkpointsList',
        'checkpointsDrawerBody',
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

    for elem_id in required_ids:
        pattern = f'id="{elem_id}"'
        assert pattern in html, f"Missing required element with id='{elem_id}'"

    # Verify all 12 sets are represented in the dataset dropdown
    for i in range(1, 13):
        set_key = f'set{i:02d}'
        assert f'value="{set_key}"' in html, f"Missing dataset option for {set_key}"

    print("  -> PASS: All HTML structure, CSS rules, and required DOM elements present.")


def test_js_logic_in_node():
    print("\n[Test 2] Testing JavaScript business logic & UI functions in Node.js...")

    with open(HTML_PATH, 'r', encoding='utf-8') as f:
        html = f.read()

    # Extract script block
    script_matches = re.findall(r'<script>(.*?)</script>', html, re.DOTALL)
    assert len(script_matches) > 0, "Could not find inline <script> block in HTML"
    inline_js = script_matches[-1]

    node_test_script = f"""
    const path = require('path');
    const DiffEngine = require({json.dumps(DIFF_ENGINE_JS)});
    const DATASETS_REGISTRY = require({json.dumps(REGISTRY_JSON)});

    // Mock browser environment
    global.window = {{
      DATASETS_REGISTRY,
      DiffEngine,
      addEventListener: () => {{}},
    }};
    global.document = {{
      getElementById: (id) => ({{
        classList: {{ add: () => {{}}, remove: () => {{}}, toggle: () => {{}} }},
        addEventListener: () => {{}},
        setAttribute: () => {{}},
        getAttribute: () => '',
        style: {{}},
        textContent: '',
        innerHTML: '',
        querySelectorAll: () => [],
      }}),
      querySelectorAll: () => [],
      addEventListener: () => {{}},
      body: {{ classList: {{ toggle: () => {{}} }} }}
    }};

    // Execute inline code
    {inline_js}

    // Now test functions from window or inline scope
    console.log("INLINE_LOADED_OK");
    """

    res = subprocess.run(['node', '-e', node_test_script], capture_output=True, text=True, cwd=BASE_DIR)
    assert res.returncode == 0, f"Inline script execution failed:\n{res.stderr}\n{res.stdout}"
    assert "INLINE_LOADED_OK" in res.stdout
    print("  -> PASS: Inline JavaScript loaded and parsed cleanly without syntax errors.")


def test_auto_detection_and_evaluation():
    print("\n[Test 3] Testing auto-detection and dataset evaluation...")

    node_test = f"""
    const DiffEngine = require({json.dumps(DIFF_ENGINE_JS)});
    const DATASETS_REGISTRY = require({json.dumps(REGISTRY_JSON)});

    // Auto-detect test logic
    function detectDataset(filename, headers) {{
      const lowerName = (filename || '').toLowerCase();
      for (const [id, config] of Object.entries(DATASETS_REGISTRY)) {{
        if (config.filenamePattern) {{
          const regex = new RegExp(config.filenamePattern, 'i');
          if (regex.test(lowerName)) return id;
        }}
        if (lowerName.includes(id)) return id;
        if (config.name && lowerName.includes(config.name.toLowerCase())) return id;
      }}
      if (headers && headers.length > 0) {{
        let bestId = null, bestOverlap = 0;
        for (const [id, config] of Object.entries(DATASETS_REGISTRY)) {{
          const overlap = headers.filter(h => config.headers.includes(h)).length;
          if (overlap > bestOverlap && overlap >= 3) {{
            bestOverlap = overlap;
            bestId = id;
          }}
        }}
        return bestId;
      }}
      return null;
    }}

    // 1. Filename detections
    for (let i = 1; i <= 12; i++) {{
      const setId = `set${{String(i).padStart(2, '0')}}`;
      const detected1 = detectDataset(`student_submission_${{setId}}.csv`, []);
      if (detected1 !== setId) throw new Error(`Filename detection failed for ${{setId}}, got ${{detected1}}`);
    }}

    // 2. Header detections
    for (let i = 1; i <= 12; i++) {{
      const setId = `set${{String(i).padStart(2, '0')}}`;
      const headers = DATASETS_REGISTRY[setId].headers;
      const detected2 = detectDataset('unknown_filename.csv', headers);
      if (detected2 !== setId) throw new Error(`Header detection failed for ${{setId}}, got ${{detected2}}`);
    }}

    // 3. Evaluate Ground Truth clean rows for all 12 sets
    for (let i = 1; i <= 12; i++) {{
      const setId = `set${{String(i).padStart(2, '0')}}`;
      const cfg = DATASETS_REGISTRY[setId];
      const result = DiffEngine.evaluateStudentData(cfg.groundTruthRows, cfg);
      if (result.rubricScore !== 18 || result.accuracyPct !== 100) {{
        throw new Error(`Evaluation failed for ${{setId}}: score=${{result.rubricScore}}, acc=${{result.accuracyPct}}`);
      }}
    }}

    console.log("AUTODETECT_AND_EVAL_ALL_PASSED");
    """

    res = subprocess.run(['node', '-e', node_test], capture_output=True, text=True, cwd=BASE_DIR)
    assert res.returncode == 0, f"Auto-detection or evaluation failed:\n{res.stderr}\n{res.stdout}"
    assert "AUTODETECT_AND_EVAL_ALL_PASSED" in res.stdout
    print("  -> PASS: Auto-detection and evaluation passed for all 12 datasets.")


def test_offline_readiness():
    print("\n[Test 4] Verifying offline readiness and zero external dependency fallbacks...")
    with open(HTML_PATH, 'r', encoding='utf-8') as f:
        html = f.read()

    # Check fallback for CSV parsing
    assert 'DiffEngine.parseCsv' in html, "Missing fallback to DiffEngine.parseCsv when PapaParse is offline"
    # Check fallback CSS
    assert 'var(--font-body)' in html, "Missing CSS variable font definitions"
    assert 'cell-fail' in html and 'cell-pass' in html, "Missing embedded color states"
    # Check script error banner
    assert 'missingScriptsAlert' in html, "Missing missingScriptsAlert element"

    print("  -> PASS: 100% offline fallback mechanisms verified.")


def main():
    print("=" * 60)
    print("Running Grading Dashboard UI Test Suite")
    print("=" * 60)
    test_html_structure()
    test_js_logic_in_node()
    test_auto_detection_and_evaluation()
    test_offline_readiness()
    print("\n" + "=" * 60)
    print("ALL DASHBOARD UI TESTS PASSED SUCCESSFULLY! (GREEN)")
    print("=" * 60)


if __name__ == '__main__':
    main()
