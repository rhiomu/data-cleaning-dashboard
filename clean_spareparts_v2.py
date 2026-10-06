import csv
import re

input_path = 'set06_spareparts.csv'
output_path = 'set06_spareparts_cleaned_v2.csv'

with open(input_path, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    fieldnames = list(reader.fieldnames)
    raw_rows = list(reader)

cleaned_rows = []
seen_ids = set()

for idx, r in enumerate(raw_rows):
    part_id = r['รหัสอะไหล่'].strip()
    part_name = r['ชื่ออะไหล่'].strip()
    category = r['หมวด'].strip()
    stock = r['คงเหลือ'].strip()
    unit = r['หน่วย'].strip()
    reorder = r['จุดสั่งซื้อ'].strip()
    location = r['ที่เก็บ'].strip()

    # 1. รหัสอะไหล่: แก้ไขตัวอักษรพิมพ์ผิด 'SP-O103' เป็น 'SP-0103'
    part_id = re.sub(r'^SP-[oO]', 'SP-0', part_id)

    # กฎทางธุรกิจ: โซลินอยด์วาล์วนับใหม่ได้ 20 ตัว แถวที่เป็น 18 เป็นยอดนับรอบก่อน ให้ลบ
    if part_id == 'SP-0109' and stock == '18':
        continue

    # ตัดแถวซ้ำ (Deduplication) สำหรับ SP-0110
    if part_id in seen_ids:
        continue
    seen_ids.add(part_id)

    # 2. ชื่ออะไหล่:
    # แก้ไขอักขระเสีย 'รีเลย์ 24\ufffd' เป็น 'รีเลย์ 24V'
    part_name = part_name.replace('\ufffd', 'V')
    # ปรับชื่อตามทะเบียนอะไหล่ใน Data Dictionary เช่น 'ท่อลม PU 8 มม.'
    if part_name == 'ท่อลม PU 8mm':
        part_name = 'ท่อลม PU 8 มม.'

    # 3. หมวด: เครื่องกล · ไฟฟ้า · ระบบลม
    if category.lower() == 'mechanical':
        category = 'เครื่องกล'
    elif category == 'ไฟฟ้า/อิเล็กทรอนิกส์':
        category = 'ไฟฟ้า'

    # 4. คงเหลือ (ข้อมูลจริงจากเจ้าของข้อมูล):
    # SP-0107: ข้อต่อลม 1/4 นิ้ว นับได้ 10 ชิ้น (เดิมเป็นค่าว่าง)
    if part_id == 'SP-0107':
        stock_clean = '10'
    # SP-0117: มอเตอร์พัดลมนับได้ 17 ตัว (เดิม 170 คือพิมพ์ 0 เกิน)
    elif part_id == 'SP-0117':
        stock_clean = '17'
    else:
        stock_clean = re.sub(r'[^\d.-]', '', stock)
        if stock_clean == '':
            stock_clean = '0'
        else:
            val = float(stock_clean)
            val = abs(val) # แก้ไข -10 เป็น 10
            stock_clean = str(int(val))

    # 5. หน่วยนับ (ตาม Data Dictionary: ตัว · เส้น · ชิ้น · หลอด · เมตร · ลิตร):
    # SP-0111: น้ำมันหล่อลื่นนับเป็นลิตร 5 ลิตรถูกแล้ว (เดิมแกลลอน)
    if part_id == 'SP-0111':
        unit = 'ลิตร'
    # SP-0105: หลอด LED 18W ใน Data Dictionary ใช้หน่วย 'หลอด' (เดิมดวง)
    elif part_id == 'SP-0105':
        unit = 'หลอด'
    elif unit == 'ม.':
        unit = 'เมตร'

    # 6. ที่เก็บ (ชั้นวาง):
    # SP-0101: ลูกปืน 6205 เก็บที่ชั้น A2 (เดิม B2 ซึ่งผิดหมวดเครื่องกล)
    if part_id == 'SP-0101':
        location = 'A2'
    else:
        location = location.replace('ชั้น', '').strip().upper()

    cleaned_rows.append({
        'รหัสอะไหล่': part_id,
        'ชื่ออะไหล่': part_name,
        'หมวด': category,
        'คงเหลือ': stock_clean,
        'หน่วย': unit,
        'จุดสั่งซื้อ': reorder,
        'ที่เก็บ': location
    })

with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(cleaned_rows)

print(f"Data successfully cleaned with Data Dictionary and saved to: {output_path}")
