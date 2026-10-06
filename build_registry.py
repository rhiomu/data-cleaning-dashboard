#!/usr/bin/env python3
"""
build_registry.py

Compiles all 12 data cleaning challenge sets into:
1. challenge/datasets_registry.json
2. challenge/datasets_registry.js (window.DATASETS_REGISTRY)

Inputs:
- groundtruth/set01_*.csv .. set12_*.csv (Ground truth cleaned CSVs)
- info/ใบเฉลย-12ชุด-แจกหลังจบรอบ.docx (18-point rubric checklist for all 12 sets)
"""

import os
import csv
import json
import re
import zipfile
import xml.etree.ElementTree as ET

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GT_DIR = os.path.join(BASE_DIR, 'groundtruth')
DOCX_PATH = os.path.join(BASE_DIR, 'info', 'ใบเฉลย-12ชุด-แจกหลังจบรอบ.docx')
JSON_OUT_PATH = os.path.join(BASE_DIR, 'datasets_registry.json')
JS_OUT_PATH = os.path.join(BASE_DIR, 'datasets_registry.js')

DATASET_CONFIGS = [
    {
        "id": "set01",
        "name": "ลงทะเบียนอบรม",
        "filenamePattern": "set01|training",
        "pkCol": "รหัสพนักงาน",
        "pkCols": ["รหัสพนักงาน"],
        "csvFile": "set01_training_cleaned.csv",
    },
    {
        "id": "set02",
        "name": "ใบแจ้งซ่อม",
        "filenamePattern": "set02|repair",
        "pkCol": "เลขที่ใบงาน",
        "pkCols": ["เลขที่ใบงาน"],
        "csvFile": "set02_repair_cleaned.csv",
    },
    {
        "id": "set03",
        "name": "เบิกค่าเดินทาง",
        "filenamePattern": "set03|travel",
        "pkCol": "เลขที่ใบเบิก",
        "pkCols": ["เลขที่ใบเบิก"],
        "csvFile": "set03_travel_cleaned.csv",
    },
    {
        "id": "set04",
        "name": "เบิกวัสดุสำนักงาน",
        "filenamePattern": "set04|supplies",
        "pkCol": "เลขที่ใบเบิก",
        "pkCols": ["เลขที่ใบเบิก"],
        "csvFile": "set04_supplies_cleaned.csv",
    },
    {
        "id": "set05",
        "name": "ใบสั่งซื้อ",
        "filenamePattern": "set05|purchase",
        "pkCol": "เลขที่ใบสั่งซื้อ",
        "pkCols": ["เลขที่ใบสั่งซื้อ"],
        "csvFile": "set05_purchase_cleaned.csv",
    },
    {
        "id": "set06",
        "name": "สต็อกอะไหล่",
        "filenamePattern": "set06|spareparts",
        "pkCol": "รหัสอะไหล่",
        "pkCols": ["รหัสอะไหล่"],
        "csvFile": "set06_spareparts_cleaned.csv",
    },
    {
        "id": "set07",
        "name": "ใช้รถส่วนกลาง",
        "filenamePattern": "set07|companycar",
        "pkCol": "เลขที่ใบขอใช้รถ",
        "pkCols": ["เลขที่ใบขอใช้รถ"],
        "csvFile": "set07_companycar_cleaned.csv",
    },
    {
        "id": "set08",
        "name": "ตรวจความปลอดภัยประจำเดือน",
        "filenamePattern": "set08|safety",
        "pkCol": "เลขที่การตรวจ",
        "pkCols": ["เลขที่การตรวจ"],
        "csvFile": "set08_safety_cleaned.csv",
    },
    {
        "id": "set09",
        "name": "ค่าไฟฟ้ารายเดือนของอาคาร",
        "filenamePattern": "set09|electricity",
        "pkCol": "เดือน+อาคาร",
        "pkCols": ["เดือน", "อาคาร"],
        "csvFile": "set09_electricity_cleaned.csv",
    },
    {
        "id": "set10",
        "name": "ทะเบียนทรัพย์สิน IT",
        "filenamePattern": "set10|itassets",
        "pkCol": "รหัสทรัพย์สิน",
        "pkCols": ["รหัสทรัพย์สิน"],
        "csvFile": "set10_itassets_cleaned.csv",
    },
    {
        "id": "set11",
        "name": "รับสินค้าเข้าคลัง",
        "filenamePattern": "set11|goodsreceipt",
        "pkCol": "เลขที่ใบรับ",
        "pkCols": ["เลขที่ใบรับ"],
        "csvFile": "set11_goodsreceipt_cleaned.csv",
    },
    {
        "id": "set12",
        "name": "บันทึกผู้มาติดต่อ",
        "filenamePattern": "set12|visitors",
        "pkCol": "เลขบัตร",
        "pkCols": ["เลขบัตร"],
        "csvFile": "set12_visitors_cleaned.csv",
    },
]


def parse_docx_tables(docx_path):
    """
    Parses all 12 tables in info/ใบเฉลย-12ชุด-แจกหลังจบรอบ.docx
    using standard zipfile and xml.etree.ElementTree.
    Returns a list of 12 rubric item lists (18 checkpoints each).
    """
    if not os.path.exists(docx_path):
        raise FileNotFoundError(f"Answer key docx not found at {docx_path}")

    with zipfile.ZipFile(docx_path) as z:
        xml_content = z.read('word/document.xml')
        tree = ET.fromstring(xml_content)

    namespaces = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    tables = tree.findall('.//w:tbl', namespaces)

    if len(tables) < 12:
        raise ValueError(f"Expected at least 12 tables in docx, found {len(tables)}")

    parsed_rubrics = []

    for t_idx in range(12):
        tbl = tables[t_idx]
        rows = tbl.findall('.//w:tr', namespaces)
        if len(rows) < 19:
            raise ValueError(f"Table {t_idx} has {len(rows)} rows, expected 19 (1 header + 18 items)")

        rubric_items = []
        for r_idx in range(1, len(rows)):
            cells = rows[r_idx].findall('.//w:tc', namespaces)
            cell_texts = [''.join(c.itertext()).strip() for c in cells]

            # Schema: ['#', 'ระดับ', 'แถว', 'คอลัมน์', 'ค่าในไฟล์', 'ค่าที่ถูก / วิธีแก้', 'ถาม', '✓']
            num_str, level, orig_row, col, orig_val, correct_raw, ask, _ = cell_texts

            item_num = int(num_str)
            is_ask_owner = ('★' in ask)

            if col == '(ทั้งแถว)':
                correct_val = correct_raw
                note = ""
            else:
                m = re.match(r'^(.*?)\s*\((.*?)\)$', correct_raw)
                if m:
                    correct_val = m.group(1).strip()
                    note = m.group(2).strip()
                else:
                    correct_val = correct_raw
                    note = ""

            rubric_item = {
                "#": item_num,
                "id": item_num,
                "level": level,
                "origRow": orig_row,
                "col": col,
                "origVal": orig_val,
                "correctVal": correct_val,
                "rawCorrectVal": correct_raw,
                "askOwner": is_ask_owner,
                "explanation": correct_raw,
                "note": note,
            }
            rubric_items.append(rubric_item)

        parsed_rubrics.append(rubric_items)

    return parsed_rubrics


def parse_groundtruth_csv(csv_path):
    """Parses ground truth CSV and returns headers list and list of row dicts."""
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Ground truth CSV not found at {csv_path}")

    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        headers = list(reader.fieldnames)
        rows = [dict(r) for r in reader]

    return headers, rows


def build_registry():
    rubrics_by_set = parse_docx_tables(DOCX_PATH)

    registry = {}
    for idx, cfg in enumerate(DATASET_CONFIGS):
        set_id = cfg["id"]
        csv_file = os.path.join(GT_DIR, cfg["csvFile"])
        headers, gt_rows = parse_groundtruth_csv(csv_file)
        rubric = rubrics_by_set[idx]

        registry[set_id] = {
            "id": set_id,
            "name": cfg["name"],
            "filenamePattern": cfg["filenamePattern"],
            "pkCol": cfg["pkCol"],
            "pkCols": cfg["pkCols"],
            "headers": headers,
            "groundTruthRows": gt_rows,
            "rubric": rubric,
        }

    # 1. Write JSON
    with open(JSON_OUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(registry, f, ensure_ascii=False, indent=2)
    print(f"Successfully generated: {JSON_OUT_PATH}")

    # 2. Write JavaScript bundle
    with open(JS_OUT_PATH, 'w', encoding='utf-8') as f:
        f.write("// Auto-generated by build_registry.py - DO NOT EDIT MANUALLY\n")
        f.write("var DATASETS_REGISTRY = ")
        f.write(json.dumps(registry, ensure_ascii=False, indent=2))
        f.write(";\n\n")
        f.write("if (typeof window !== 'undefined') {\n")
        f.write("  window.DATASETS_REGISTRY = DATASETS_REGISTRY;\n")
        f.write("}\n")
        f.write("if (typeof module !== 'undefined' && module.exports) {\n")
        f.write("  module.exports = DATASETS_REGISTRY;\n")
        f.write("}\n")
    print(f"Successfully generated: {JS_OUT_PATH}")

    return registry


if __name__ == '__main__':
    build_registry()
