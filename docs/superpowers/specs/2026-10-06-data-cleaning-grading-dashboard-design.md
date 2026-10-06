# Data Cleaning Grading Dashboard - Design Specification

## 1. Overview & Objective
A standalone, zero-installation web-based presentation and evaluation dashboard designed for an instructor to project on a large screen/projector in a classroom. The tool evaluates student-submitted CSV files for 12 data cleaning challenge sets against official Ground Truth files and displays cell-by-cell visual diffs, accuracy scores, and interactive explanations directly sourced from the official answer keys.

## 2. Key Requirements & Features

### 2.1 Multi-Dataset Support (12 Challenge Sets)
- Pre-bundled with all 12 challenge datasets located in `challenge/groundtruth/set01_*.csv` to `set12_*.csv`:
  1. `set01_training`: ลงทะเบียนอบรม (PK: รหัสพนักงาน)
  2. `set02_repair`: ใบแจ้งซ่อม (PK: เลขที่ใบงาน)
  3. `set03_travel`: เบิกค่าเดินทาง (PK: เลขที่ใบเบิก)
  4. `set04_supplies`: เบิกวัสดุสำนักงาน (PK: เลขที่ใบเบิก)
  5. `set05_purchase`: ใบสั่งซื้อ (PK: เลขที่ใบสั่งซื้อ)
  6. `set06_spareparts`: สต็อกอะไหล่ (PK: รหัสอะไหล่)
  7. `set07_companycar`: ใช้รถส่วนกลาง (PK: เลขที่ใบขอใช้รถ)
  8. `set08_safety`: ตรวจความปลอดภัยประจำเดือน (PK: เลขที่การตรวจ)
  9. `set09_electricity`: ค่าไฟฟ้ารายเดือนของอาคาร (PK: เดือน + อาคาร / เดือน)
  10. `set10_itassets`: ทะเบียนทรัพย์สิน IT (PK: รหัสทรัพย์สิน)
  11. `set11_goodsreceipt`: รับสินค้าเข้าคลัง (PK: เลขที่ใบรับ)
  12. `set12_visitors`: บันทึกผู้มาติดต่อ (PK: เลขบัตร)
- **Auto-Detection**: Automatically identifies the challenge set when a CSV is dropped, based on filename keywords (e.g., `set06`, `spareparts`) or column header fingerprints.
- **Manual Override**: Dropdown menu at the top allows the instructor to explicitly switch between all 12 sets at any time.

### 2.2 Row Alignment & Smart Matching
- **Primary Key Matching**: Rows are aligned using the dataset's Primary Key column to prevent cascading row-shift errors caused by sorting, row insertions, or omitted deletions.
- **Duplicate & Extra Row Detection**: Unremoved duplicates or unexpected rows are explicitly highlighted with warning badges (`[แถวเกิน/ลืมลบ]`).
- **Missing Row Detection**: Omitted rows from ground truth are flagged with warning badges (`[แถวขาดหายไป]`).
- **Smart Value Normalization**:
  - Automatically trims leading and trailing whitespace.
  - Number equivalence matching (e.g. `10` vs `10.0`, formatted numbers like `1,000` vs `1000`).
  - Strict preservation of business rules (e.g. case sensitivity where specified in data dictionary like `c1` -> `C1`).

### 2.3 Interactive Cell-by-Cell Presentation Grid
- **Pass (Green)**: Soft green background with crisp dark green text indicating correct cleaning.
- **Fail (Red)**: Soft red background displaying the student's submission.
- **Click/Hover to Reveal**:
  - Clicking any red cell smoothly reveals a pedagogical detail card:
    - **Student Answer vs Ground Truth Answer**
    - **Official 18-Point Rubric Checkpoint Info** (extracted from `info/ใบเฉลย-12ชุด-แจกหลังจบรอบ.docx`):
      - Checkpoint # and Difficulty Badge (`ง่าย`, `กลาง`, `ยาก`)
      - Original file flaw (`ค่าในไฟล์`)
      - Correct method / domain rationale (`ค่าที่ถูก / วิธีแก้`)
      - Domain Knowledge Star Badge (`★ ต้องถามเจ้าของข้อมูล`)
- **Quick Controls**:
  - "Reveal All (เฉลยทั้งหมด)": Uncovers all answers instantly.
  - "Hide All (ซ่อนเฉลย)": Re-hides answers to continue testing students.
  - "Projector Mode (ขยายจอใหญ่)": Enlarges font size and optimizes contrast for long-distance readability.

### 2.4 Dual Scoring Engine
1. **Official Rubric Score (18 Checkpoints)**:
   - Evaluates each of the 18 specific challenge rubric items from `info/ใบเฉลย-12ชุด-แจกหลังจบรอบ.docx`.
   - Score displayed prominently: `X / 18 คะแนน`.
   - Star Score: `Y / N ข้อดาว (★)` highlighting student mastery of stakeholder interviews.
   - Expandable 18-point checklist drawer showing status per checkpoint.
2. **Cell-by-Cell Accuracy Score**:
   - Total correct cells out of all table cells (e.g. `124 / 126 ช่อง (98.4%)`).
   - Column-by-column breakdown bar highlighting which columns had the most student errors.

## 3. System Architecture & Tech Stack

### 3.1 File Structure
- `challenge/grading_dashboard.html`: Single-file standalone web application containing:
  - HTML5 semantics
  - Embedded Tailwind CSS (via CDN with fallback offline styling)
  - Embedded PapaParse (for robust, high-performance in-browser CSV parsing with UTF-8 and BOM handling)
  - Embedded Dataset Registry (`DATASETS_REGISTRY`): Pre-compiled JSON structure containing Ground Truth data and the 18-point rubric checklist for all 12 challenge sets.

### 3.2 Data Flow Pipeline
```
[Student CSV File] 
        │
        ▼ (Drag & Drop or File Input)
[PapaParse Engine] ───► Clean Raw Matrix & Headers
        │
        ▼
[Dataset Auto-Detector] ───► Match against Set 01–12 Registry
        │
        ▼
[Smart Alignment & Diff Engine]
        ├── 1. Primary Key Alignment
        ├── 2. Extra/Missing Row Detection
        ├── 3. Cell Normalization & Comparison
        └── 4. 18-Point Official Rubric Evaluation
        │
        ▼
[State Management & UI Renderer]
        ├── Metric Cards (Total Score / 18, Star Points, Accuracy %)
        ├── 18 Checkpoints Interactive Drawer
        └── Presentation Grid with Click-to-Reveal Tooltips
```

## 4. Verification & Testing Plan
- Test with the original uncleaned file `challenge/set06_spareparts.csv` -> Verify score is 0/18 (all 18 checkpoints red and explanation cards correctly populated).
- Test with our cleaned file `challenge/set06_spareparts_cleaned_v2.csv` -> Verify score is 18/18 (100% green).
- Test with partially cleaned / edge case files (e.g. inverted row order, unremoved duplicates, missing columns) -> Verify that Primary Key matching handles order changes seamlessly without row offsets.
