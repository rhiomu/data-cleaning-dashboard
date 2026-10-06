/**
 * diff_engine.js - Diff & Evaluation Engine for Data Cleaning Grading Dashboard
 *
 * Provides:
 * - Smart Primary Key row alignment (single PK and composite PK).
 * - Duplicate & extra row detection.
 * - Missing row detection.
 * - Cell value normalization (trimming, numeric equivalence like 10 vs 10.0 or 1,000 vs 1000).
 * - Official 18-point rubric checklist scoring with star questions (askOwner).
 * - Cell-by-cell visual diff matrix with pedagogical explanation popovers.
 *
 * Compatible with both Node.js (module.exports) and Browser (window.DiffEngine).
 */

(function () {
  /**
   * Simple zero-dependency CSV parser handling quoted values, commas, and CRLF.
   */
  function parseCsv(csvText) {
    if (!csvText || typeof csvText !== 'string') return [];
    const lines = [];
    let row = [];
    let field = '';
    let inQuotes = false;

    // Normalize newlines
    const text = csvText.replace(/\r\n/g, '\n').replace(/\r/g, '\n');

    for (let i = 0; i < text.length; i++) {
      const char = text[i];
      const nextChar = text[i + 1];

      if (char === '"') {
        if (inQuotes && nextChar === '"') {
          field += '"';
          i++; // skip escaped quote
        } else {
          inQuotes = !inQuotes;
        }
      } else if (char === ',' && !inQuotes) {
        row.push(field);
        field = '';
      } else if (char === '\n' && !inQuotes) {
        row.push(field);
        field = '';
        if (row.length > 0 && !(row.length === 1 && row[0] === '')) {
          lines.push(row);
        }
        row = [];
      } else {
        field += char;
      }
    }
    if (field !== '' || row.length > 0) {
      row.push(field);
      if (row.length > 0 && !(row.length === 1 && row[0] === '')) {
        lines.push(row);
      }
    }

    if (lines.length < 2) return [];
    const headers = lines[0].map(h => h.trim().replace(/^\uFEFF/, ''));
    const rows = [];
    for (let r = 1; r < lines.length; r++) {
      const line = lines[r];
      const obj = {};
      for (let c = 0; c < headers.length; c++) {
        obj[headers[c]] = line[c] !== undefined ? line[c].trim() : '';
      }
      rows.push(obj);
    }
    return rows;
  }

  /**
   * Normalizes a cell value for clean comparison.
   */
  function normalizeCellValue(val) {
    if (val === null || val === undefined) return '';
    return String(val).trim();
  }

  /**
   * Checks if string is a number with optional commas and optional decimal points.
   */
  function isNumericString(str) {
    if (!str || typeof str !== 'string') return false;
    // Allow numbers like "1,000", "10", "10.0", "-20", "27,190"
    return /^-?(\d{1,3}(,\d{3})*|\d+)(\.\d+)?$/.test(str.trim());
  }

  /**
   * Parses number by removing thousand commas.
   */
  function parseNumberClean(str) {
    return parseFloat(String(str).replace(/,/g, '').trim());
  }

  /**
   * Determines if student cell value matches ground truth cell value,
   * taking into account whitespace normalization, numeric equivalence,
   * and ensuring that uncleaned flawed states from the rubric are not accepted.
   */
  function areCellsEqual(studentVal, gtVal, rubricItem) {
    const s1 = normalizeCellValue(studentVal);
    const s2 = normalizeCellValue(gtVal);

    // Exact string match after trimming
    if (s1 === s2) return true;

    // If this cell has a known rubric flaw, ensure student value is NOT the raw flaw
    if (rubricItem) {
      const origFlaw = normalizeCellValue(rubricItem.origVal);
      if (origFlaw === '(ว่าง)' || origFlaw === '') {
        if (s1 === '') return false;
      } else {
        if (s1 === origFlaw) return false;
      }
    }

    // Check numeric equivalence (e.g. 10 vs 10.0, 1,000 vs 1000)
    if (isNumericString(s1) && isNumericString(s2)) {
      const n1 = parseNumberClean(s1);
      const n2 = parseNumberClean(s2);
      if (!isNaN(n1) && !isNaN(n2) && Math.abs(n1 - n2) < 1e-9) {
        return true;
      }
    }

    return false;
  }

  /**
   * Extracts composite or single Primary Key string for a given row.
   */
  function getPrimaryKey(row, pkCols) {
    if (!row) return '';
    if (!pkCols || pkCols.length === 0) return '';
    if (pkCols.length === 1) {
      const val = row[pkCols[0]];
      return normalizeCellValue(val);
    }
    return pkCols.map(col => normalizeCellValue(row[col])).join('|');
  }

  /**
   * Maps 18 rubric checkpoints to Ground Truth rows using verified deletion offset.
   */
  function getRubricGtMappings(rubric, gtRows, pkCols) {
    const dupItems = rubric.filter(r => r.col === '(ทั้งแถว)');
    const delIndices = [];
    dupItems.forEach(d => {
      const nums = (String(d.origRow).match(/\d+/g) || []).map(Number);
      if (nums.length > 0) {
        delIndices.push(Math.max(...nums));
      }
    });
    delIndices.sort((a, b) => a - b);

    return rubric.map(item => {
      const isRowLevel = item.col === '(ทั้งแถว)';
      const nums = (String(item.origRow).match(/\d+/g) || []).map(Number);
      const rawRow = nums.length > 0 ? Math.min(...nums) : 1;
      const shift = delIndices.filter(di => di < rawRow).length;
      const gtIndex = Math.max(0, Math.min(gtRows.length - 1, rawRow - 1 - shift));
      const targetGtRow = gtRows[gtIndex];
      const targetGtPk = getPrimaryKey(targetGtRow, pkCols);

      // Check if item specifies a bogus PK to delete (e.g. "ลบ TR-19")
      let bogusPk = null;
      if (isRowLevel && item.correctVal) {
        const m = item.correctVal.match(/ลบ\s+([A-Za-z0-9\-_]+)/);
        if (m) bogusPk = m[1].trim();
      }

      return {
        item,
        isRowLevel,
        rawRow,
        gtIndex,
        targetGtRow,
        targetGtPk,
        bogusPk,
      };
    });
  }

  /**
   * Main evaluation function.
   *
   * @param {Array|string} studentRows - Array of row objects or raw CSV text
   * @param {Object} datasetConfig - Entry from datasets_registry
   * @returns {Object} Comprehensive evaluation result
   */
  function evaluateStudentData(studentRows, datasetConfig) {
    if (!datasetConfig) {
      throw new Error("datasetConfig is required for evaluateStudentData");
    }

    // Support CSV string or PapaParse object
    let rows = studentRows;
    if (typeof rows === 'string') {
      rows = parseCsv(rows);
    } else if (rows && typeof rows === 'object' && Array.isArray(rows.data)) {
      rows = rows.data;
    }
    if (!Array.isArray(rows)) {
      rows = [];
    }

    const pkCols = datasetConfig.pkCols || (datasetConfig.pkCol ? [datasetConfig.pkCol] : []);
    const headers = datasetConfig.headers || [];
    const gtRows = datasetConfig.groundTruthRows || [];
    const rubric = datasetConfig.rubric || [];

    // Clean up student rows and trim keys
    const studentList = rows.map((r, idx) => {
      const cleanObj = {};
      for (const k of Object.keys(r)) {
        const cleanKey = k.trim().replace(/^\uFEFF/, '');
        cleanObj[cleanKey] = r[k];
      }
      return {
        row: cleanObj,
        idx,
        pk: getPrimaryKey(cleanObj, pkCols),
        matchedGtIdx: null,
      };
    });

    // Map rubric items to Ground Truth rows
    const rubricMappings = getRubricGtMappings(rubric, gtRows, pkCols);

    // Map known dirty PKs from rubric (e.g. SP-O103 -> SP-0103)
    const dirtyPkToGtPk = {};
    rubricMappings.forEach(m => {
      if (!m.isRowLevel && pkCols.includes(m.item.col)) {
        const dirtyKey = normalizeCellValue(m.item.origVal);
        if (dirtyKey) {
          dirtyPkToGtPk[dirtyKey] = m.targetGtPk;
        }
      }
    });

    // Ground Truth alignment tracker
    const gtList = gtRows.map((r, idx) => ({
      row: r,
      idx,
      pk: getPrimaryKey(r, pkCols),
      matchedStudentIdx: null,
    }));

    // Function to calculate cell matches between student row and GT row
    function countCellMatches(sRow, gRow) {
      let matches = 0;
      for (const h of headers) {
        if (areCellsEqual(sRow[h], gRow[h])) {
          matches++;
        }
      }
      return matches;
    }

    // --- Phase 1: Exact PK matching ---
    gtList.forEach(g => {
      const candidates = studentList.filter(s => s.matchedGtIdx === null && s.pk === g.pk);
      if (candidates.length > 0) {
        // Pick best matching candidate (highest cell agreement)
        candidates.sort((a, b) => {
          const scoreB = countCellMatches(b.row, g.row);
          const scoreA = countCellMatches(a.row, g.row);
          if (scoreB !== scoreA) return scoreB - scoreA;
          return a.idx - b.idx;
        });
        const best = candidates[0];
        best.matchedGtIdx = g.idx;
        g.matchedStudentIdx = best.idx;
      }
    });

    // --- Phase 2: Known dirty PK matching (from rubric typos) ---
    gtList.forEach(g => {
      if (g.matchedStudentIdx === null) {
        // Find if this GT row has an expected dirty PK
        for (const [dirtyPk, targetPk] of Object.entries(dirtyPkToGtPk)) {
          if (targetPk === g.pk) {
            const candidate = studentList.find(s => s.matchedGtIdx === null && s.pk === dirtyPk);
            if (candidate) {
              candidate.matchedGtIdx = g.idx;
              g.matchedStudentIdx = candidate.idx;
              break;
            }
          }
        }
      }
    });

    // --- Phase 3: Fuzzy similarity matching for remaining rows ---
    gtList.forEach(g => {
      if (g.matchedStudentIdx === null) {
        const unmatchedStudents = studentList.filter(s => s.matchedGtIdx === null);
        let bestStudent = null;
        let maxMatches = -1;
        const threshold = Math.max(2, Math.floor(headers.length / 2));

        unmatchedStudents.forEach(s => {
          const mCount = countCellMatches(s.row, g.row);
          if (mCount >= threshold && mCount > maxMatches) {
            maxMatches = mCount;
            bestStudent = s;
          }
        });

        if (bestStudent) {
          bestStudent.matchedGtIdx = g.idx;
          g.matchedStudentIdx = bestStudent.idx;
        }
      }
    });

    // --- Identify Extra Rows ---
    const extraRows = [];
    studentList.forEach(s => {
      if (s.matchedGtIdx === null) {
        // Determine duplicate vs unexpected
        const isDuplicatePk = gtList.some(g => g.pk === s.pk);
        const isBogusRubricPk = rubricMappings.some(m => m.bogusPk && m.bogusPk === s.pk);
        const reason = (isDuplicatePk || isBogusRubricPk) ? 'duplicate' : 'unexpected';
        extraRows.push({
          row: s.row,
          rowIndex: s.idx + 1,
          pk: s.pk,
          reason,
        });
      }
    });

    // --- Identify Missing Rows ---
    const missingRows = [];
    gtList.forEach(g => {
      if (g.matchedStudentIdx === null) {
        missingRows.push({
          row: g.row,
          gtIndex: g.idx,
          pk: g.pk,
        });
      }
    });

    // --- Build Matched Rows Matrix ---
    // Cell lookup helper for rubric items
    const rubricCellMap = {};
    rubricMappings.forEach(m => {
      if (!m.isRowLevel) {
        const key = `${m.gtIndex}_${m.item.col}`;
        rubricCellMap[key] = m.item;
      }
    });

    let correctCells = 0;
    const totalCells = gtRows.length * headers.length;

    const matchedRows = [];
    gtList.forEach(g => {
      if (g.matchedStudentIdx !== null) {
        const s = studentList[g.matchedStudentIdx];
        const rowDiff = {
          pk: g.pk,
          gtIndex: g.idx,
          studentIndex: s.idx,
          studentRow: s.row,
          gtRow: g.row,
          cells: {},
        };

        headers.forEach(h => {
          const sVal = s.row[h] !== undefined ? s.row[h] : '';
          const gVal = g.row[h] !== undefined ? g.row[h] : '';
          const rubItem = rubricCellMap[`${g.idx}_${h}`] || null;

          const isMatch = areCellsEqual(sVal, gVal, rubItem);
          if (isMatch) correctCells++;

          const cellInfo = {
            val: sVal,
            gtVal: gVal,
            status: isMatch ? 'match' : 'mismatch',
            isCorrect: isMatch,
            explanation: rubItem ? (rubItem.explanation || rubItem.rawCorrectVal) : '',
            rubricRef: rubItem,
          };

          rowDiff.cells[h] = cellInfo;
          rowDiff[h] = cellInfo; // Direct access convenience
        });

        matchedRows.push(rowDiff);
      }
    });

    const accuracyPct = totalCells > 0 ? Number(((correctCells / totalCells) * 100).toFixed(1)) : 0;

    // --- Evaluate 18 Rubric Checkpoints ---
    const rubricResults = [];
    let rubricScore = 0;
    let starScore = 0;
    let starMax = 0;

    rubricMappings.forEach(m => {
      const item = m.item;
      if (item.askOwner) starMax++;

      let passed = false;
      let studentVal = null;

      if (!m.isRowLevel) {
        // Cell-level Checkpoint
        const matchedRow = matchedRows.find(r => r.gtIndex === m.gtIndex);
        if (!matchedRow) {
          passed = false;
          studentVal = '(ไม่มีแถวนี้)';
        } else {
          studentVal = matchedRow.studentRow[item.col];
          const gtVal = m.targetGtRow[item.col];
          const matches = areCellsEqual(studentVal, gtVal, item);
          const rawOrig = normalizeCellValue(item.origVal);
          const studentNorm = normalizeCellValue(studentVal);

          // Must match cleaned GT and not equal original flaw (unless flaw and correctVal are identical after trimming)
          if (matches) {
            if (rawOrig === '(ว่าง)' || rawOrig === '') {
              passed = (studentNorm !== '');
            } else if (rawOrig === normalizeCellValue(item.correctVal)) {
              passed = true;
            } else {
              passed = (studentNorm !== rawOrig);
            }
          } else {
            passed = false;
          }
        }
      } else {
        // Row-level Duplicate Checkpoint
        if (m.bogusPk) {
          // Checkpoint expects bogus PK to be deleted (e.g. ลบ TR-19)
          const isPartnerMissing = missingRows.some(mr => mr.pk === m.targetGtPk);
          const foundInExtra = extraRows.some(e => e.pk === m.bogusPk);
          const foundInStudent = studentList.some(s => s.pk === m.bogusPk);
          if (isPartnerMissing) {
            passed = false;
            studentVal = 'แถวที่ถูกต้องขาดหายไป';
          } else if (foundInExtra || foundInStudent) {
            passed = false;
            studentVal = `พบค้างอยู่ในข้อมูล (${m.bogusPk})`;
          } else {
            passed = true;
            studentVal = `ลบ ${m.bogusPk} แล้ว`;
          }
        } else {
          // Checkpoint on duplicate rows sharing the same PK
          const targetPk = m.targetGtPk;
          const hasDuplicateExtra = extraRows.some(e => e.pk === targetPk);
          const isMissing = missingRows.some(mr => mr.pk === targetPk);

          if (hasDuplicateExtra) {
            passed = false;
            studentVal = 'พบแถวซ้ำ (ยังไม่ได้ลบ)';
          } else if (isMissing) {
            passed = false;
            studentVal = 'แถวขาดหายไป';
          } else {
            // Exactly 1 row exists. Verify it matches the expected cleaned GT state
            const matchedRow = matchedRows.find(r => r.gtIndex === m.gtIndex);
            if (matchedRow) {
              // Check if all cells of this row match
              const allMatch = headers.every(h => matchedRow.cells[h].status === 'match');
              if (allMatch) {
                passed = true;
                studentVal = 'ลบแถวซ้ำแล้ว (ข้อมูลถูกต้อง)';
              } else {
                passed = false;
                studentVal = 'เลือกแถวผิดหรือไม่ตรงตามเฉลย';
              }
            } else {
              passed = false;
              studentVal = 'แถวขาดหายไป';
            }
          }
        }
      }

      if (passed) {
        rubricScore++;
        if (item.askOwner) starScore++;
      }

      rubricResults.push({
        item,
        passed,
        studentVal,
      });
    });

    return {
      totalCells,
      correctCells,
      accuracyPct,
      rubricScore,
      rubricMax: rubric.length,
      starScore,
      starMax,
      rubricResults,
      matchedRows,
      extraRows,
      missingRows,
    };
  }

  // Export for browser
  if (typeof window !== 'undefined') {
    window.DiffEngine = {
      evaluateStudentData,
      parseCsv,
      normalizeCellValue,
      areCellsEqual,
      getPrimaryKey,
    };
  }

  // Export for Node.js
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
      evaluateStudentData,
      parseCsv,
      normalizeCellValue,
      areCellsEqual,
      getPrimaryKey,
    };
  }
})();
