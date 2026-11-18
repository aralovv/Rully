# Controlled Remediation Sprint Report: Uzbekistan Driving Test Master Database

**Project Name:** Uzbekistan Official Driving Test Master Database (YHQ / Avtotest)  
**Engineering Role:** Principal Data Engineer, Database Reliability Engineer, Python QA Architect & Regulatory Data Verification Specialist  
**Sprint Type:** Controlled Remediation Sprint (Defect Correction, Deduplication Refinement, Source Trace Cleansing, Regulatory Verification Rebuild, Full QA Validation & Deliverables Regeneration)  
**Execution Date:** November 16, 2026  
**Safety Protocol:** 10/10 Non-Negotiable Safety Rules Fully Enforced (Forensic snapshot preserved, zero question records deleted, zero answer texts mutated, zero original images altered).  
**Sprint Working Directory:** [c:\Users\Администратор\AvtoTest](file:///c:/Users/Администратор/AvtoTest)

---

## 1. Executive Verdict & Summary

### **FINAL VERDICT: PASS WITH FINDINGS**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            EXECUTIVE VERDICT                                │
│                                                                             │
│                    >>>   PASS WITH FINDINGS   <<<                           │
│                                                                             │
│  All 6 stages of the Controlled Remediation Sprint have been successfully   │
│  executed and independently verified. The 40-record source discrepancy has  │
│  been permanently eliminated by archiving 306 prototype duplicates, bringing│
│  question_sources to exactly 7,383 clean traces protected by a unique index.│
│  The deduplication defect was resolved: 1,379 distinct visual scenarios are │
│  safely preserved, and the verification engine was completely rebuilt to     │
│  reflect statutory reality with multilingual support. 17 of 17 tests passed.│
│  The "Findings" reflect 9 upstream raw-source option typos and the ongoing  │
│  unreleased status of the internal state exam software database.           │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Remediation Scorecard
| Stage & Dimension | Pre-Remediation Baseline | Post-Remediation State | Delta / Result | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Stage 0: Forensic Backup** | No snapshot archive | `backups/forensic_snapshot_pre_remediation/` | Byte-consistent online SQLite backup + SHA-256 manifest | **PASS (100%)** |
| **Stage 1: Deduplication Logic** | 1,541 false conflicts (ignored images) | 1,379 `DISTINCT_VISUAL_SCENARIO` preserved | 923 visual questions restored; 0 questions deleted | **PASS (100%)** |
| **Stage 2: Source Trace Cleansing** | 7,689 rows (306 prototype duplicates) | **7,383 clean rows** + unique index | 306 duplicates archived in DB & CSV; 0 orphans | **PASS (100%)** |
| **Stage 3: Verification Engine** | Regex hits called "Official Confirmed" | Multi-tier: `LEGAL_REFERENCE_FOUND` (3,138) | Strict statutory taxonomy; full legal metadata stored | **PASS (100%)** |
| **Stage 4: Automated Test Suite** | 11 tests with `LIMIT 50` / `LIMIT 200` | **17 tests covering ALL records (NO LIMIT)** | All 5,945 questions, 19,472 options, 1,423 images verified | **PASS (100%)** |
| **Stage 5: Master Deliverables** | Mismatched coverage report | All exports 100% regenerated and synced | SQLite, JSON, CSV, XLSX, Reports in total harmony | **PASS (100%)** |
| **Stage 6: Comparative Audit** | 40-record reporting discrepancy | Exact mathematical reconciliation | Zero data loss, zero regression | **PASS (100%)** |

---

## 2. Stage 0 — Backup, Baseline & Forensic Snapshot

Prior to performing any modifications, a complete forensic snapshot was taken in strict compliance with Safety Rules 1, 2, and 3.

### 2.1 Backup Execution & Integrity Verification
1. **Online SQLite Backup:** Executed via Python `sqlite3.connect().backup()` to produce a byte-consistent copy of the production database at `backups/forensic_snapshot_pre_remediation/master_database.sqlite`.
2. **Export & Report Preservation:** All existing deliverables ([questions.json](file:///c:/Users/Администратор/AvtoTest/questions.json), [questions.csv](file:///c:/Users/Администратор/AvtoTest/questions.csv), [questions.xlsx](file:///c:/Users/Администратор/AvtoTest/questions.xlsx), [duplicate_report.csv](file:///c:/Users/Администратор/AvtoTest/duplicate_report.csv), [verification_report.csv](file:///c:/Users/Администратор/AvtoTest/verification_report.csv), [source_coverage_report.csv](file:///c:/Users/Администратор/AvtoTest/source_coverage_report.csv), [source_registry.json](file:///c:/Users/Администратор/AvtoTest/source_registry.json), [MASTER_DATABASE_REPORT.md](file:///c:/Users/Администратор/AvtoTest/MASTER_DATABASE_REPORT.md), [INDEPENDENT_AUDIT_REPORT.md](file:///c:/Users/Администратор/AvtoTest/INDEPENDENT_AUDIT_REPORT.md)) were archived with timestamps.
3. **Integrity Validation:** Executed `PRAGMA integrity_check;` (`ok`) and `PRAGMA foreign_key_check;` (0 violations) on the backup file.
4. **Manifest Generation:** Created `backups/forensic_snapshot_pre_remediation/BACKUP_MANIFEST.json` containing SHA-256 checksums and file sizes for all backup assets.
5. **Dedicated Working Database:** Created [working_master_database.sqlite](file:///c:/Users/Администратор/AvtoTest/working_master_database.sqlite) as an isolated environment for all remediation stages.

---

## 3. Stage 1 — Deduplication Engine Remediation

### 3.1 Defect Root Cause & Fix
In the legacy deduplication engine ([`src/deduplication_engine.py`](file:///c:/Users/Администратор/AvtoTest/src/deduplication_engine.py#L93-L97)), the code computed `images_match` on line 94 but omitted it from the condition on line 97:
```python
# DEFECTIVE LEGACY LOGIC:
images_match = (base_img_sha == other_img_sha) or (base_img_sha is None or other_img_sha is None)
if base_correct and other_correct:  # <-- images_match was never checked!
    if base_correct == other_correct: exact_dups.append(...)
    else: conflicts.append(...)
```

Because driving exam questions frequently reuse standardized text prompts (*"Who crosses second?"*, *"Which vehicle moves first?"*, *"What is this sign called?"*) with completely different intersection illustrations, 923 distinct visual scenarios had been falsely classified as answer conflicts, and 461 distinct visual scenarios had been falsely classified as exact matches.

### 3.2 Implemented Conservative Strategy
The deduplication engine was rewritten in [`src/deduplication_engine.py`](file:///c:/Users/Администратор/AvtoTest/src/deduplication_engine.py) to implement a strict 4-category taxonomy:
* **Category A (Different Non-Null Image Hashes):** Classified as `DISTINCT_VISUAL_SCENARIO` (`PRESERVED_DISTINCT`). Never merged or flagged as conflict solely due to shared prompt text.
* **Category B (Same Non-Null Image Hash):** Evaluates complete normalized option sets (Jaccard similarity $\ge 0.9$) and correct answer text. Matches become `EXACT_TEXT_AND_ANSWER` (`CONFIRMED_MATCH`); contradictions become `CONFLICTING_CORRECT_ANSWER` (`CONFLICT_DETECTED`).
* **Category C (Both Images Missing / Text-Only):** Evaluates complete option sets. Identical option sets with matching answers become `EXACT_TEXT_AND_ANSWER` (`CONFIRMED_MATCH`); differing option sets (testing different subclauses of the rule) become `DISTINCT_OPTION_SUBCLAUSES` (`POTENTIAL_DUPLICATE_REVIEW`).
* **Category D (Asymmetric Image):** Where one question has an image and the other is text-only, classified as `ASYMMETRIC_IMAGE_REVIEW` (`POTENTIAL_DUPLICATE_REVIEW`). Never assumed equivalent.

### 3.3 Comparative Results (Old vs New Classification)
All 2,320 pairs from [duplicate_report.csv](file:///c:/Users/Администратор/AvtoTest/duplicate_report.csv) were re-evaluated:

| Legacy Classification | Legacy Count | Remediated Classification | Remediated Status | Remediated Count | Detailed Rationale |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **CONFLICTING_CORRECT_ANSWER** | 1,541 | `DISTINCT_VISUAL_SCENARIO` | `PRESERVED_DISTINCT` | **919** | Different intersection/sign images; questions are distinct scenarios. |
| | | `ASYMMETRIC_IMAGE_REVIEW` | `POTENTIAL_DUPLICATE_REVIEW` | **4** | Asymmetric visual asset (one image, one text). Flagged for review. |
| | | `DISTINCT_OPTION_SUBCLAUSES`| `POTENTIAL_DUPLICATE_REVIEW` | **615** | Text-only questions testing different subclauses with different options. |
| | | `EXACT_TEXT_AND_ANSWER` | `CONFIRMED_MATCH` | **3** | True text-only duplicate questions with identical options and answer. |
| **EXACT_TEXT_AND_ANSWER** | 779 | `DISTINCT_VISUAL_SCENARIO` | `PRESERVED_DISTINCT` | **460** | Different visual assets with identical answer letters (e.g. "1" or "A"). |
| | | `ASYMMETRIC_IMAGE_REVIEW` | `POTENTIAL_DUPLICATE_REVIEW` | **1** | Asymmetric visual asset. |
| | | `DISTINCT_OPTION_SUBCLAUSES`| `POTENTIAL_DUPLICATE_REVIEW` | **243** | Shared template prompt with distinct options. |
| | | `EXACT_TEXT_AND_ANSWER` | `CONFIRMED_MATCH` | **75** | True text-only duplicates with matching option sets and correct answers. |
| **TOTAL PAIRS EVALUATED** | **2,320** | | | **2,320** | **100% reconciled down to the single pair.** |

*Per Safety Rule 4 & 5: Zero questions were deleted, and zero answer keys were modified.*

---

## 4. Stage 2 — Source Trace Cleansing & Archival

### 4.1 Investigation of the 306 Prototype Records
Forensic analysis revealed that early prototype runs (`run_phase1_prototype.py`, executed between `09:28` and `09:33`) inserted 306 records into `question_sources`. When full acquisition (`acquire_all.py`) ran, it re-ingested all tickets without clearing `question_sources`, creating duplicate source traces.

### 4.2 Proposed Cleanup & Verification Procedure
1. **Creation of Proposed Cleanup Table:** A temporary audit table `proposed_source_trace_cleanup` was created in SQLite.
2. **Counterpart Verification Query:**
   ```sql
   SELECT id, collection_timestamp FROM question_sources
   WHERE source_id = ? AND original_language = ? 
     AND original_ticket = ? AND original_position = ? 
     AND question_id = ? AND id != ?
     AND collection_timestamp >= '2026-11-16 09:40:00';
   ```
   **Result:** Exactly **306 of 306** candidate prototype records were confirmed to possess an identical, valid retained counterpart in the full run. Zero records were unmatched.
3. **Archival Table Creation:** Created permanent table `archived_duplicate_source_traces` in `working_master_database.sqlite`, copying all 306 rows with their `retained_counterpart_id` and archival timestamp.
4. **Archival CSV Export:** Exported `backups/forensic_snapshot_pre_remediation/archived_duplicate_source_traces.csv`.
5. **Controlled Deletion:** Removed the 306 verified duplicate rows from `question_sources`.
6. **Orphan Validation:** Checked `questions` coverage:
   ```sql
   SELECT COUNT(DISTINCT q.id) FROM questions q
   JOIN question_sources qs ON q.id = qs.question_id;
   -- Result: 5,945 / 5,945 (100% complete; 0 orphaned questions)
   ```
7. **Unique Index Enforcement:**
   ```sql
   CREATE UNIQUE INDEX idx_question_sources_unique_trace 
   ON question_sources(source_id, original_language, original_ticket, original_position, question_id);
   ```

### 4.3 Verified Clean Source Distribution
$$\text{Clean Total} = 7,689 - 306 = \mathbf{7,383} \text{ records}$$

| Source Code | Source Name | Language | Original Records | Cleaned Duplicates | Retained Clean Records | Unique Questions Mapped |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `yesprava` | YesPrava | `ru` | 1,288 | 40 | **1,248** | 1,237 |
| `yesprava` | YesPrava | `uz_cyrl` | 1,288 | 40 | **1,248** | 1,240 |
| `yesprava` | YesPrava | `uz_latn` | 1,354 | 106 | **1,248** | 1,237 |
| `propdd` | ProPDD | `ru` | 1,253 | 40 | **1,213** | 1,205 |
| `propdd` | ProPDD | `uz_cyrl` | 1,253 | 40 | **1,213** | 1,205 |
| `propdd` | ProPDD | `uz_latn` | 1,253 | 40 | **1,213** | 1,205 |
| **TOTALS** | | | **7,689** | **306** | **7,383** | **5,945** |

The 40-record discrepancy reported in the forensic audit is permanently resolved.

---

## 5. Stage 3 — Rebuilt Verification System

### 5.1 Elimination of Misleading Assumptions
The legacy assumption that a regex hit in a third-party explanation string constitutes "Official Document Confirmation" was removed. A strict, legally grounded taxonomy was implemented in [`src/verification_engine.py`](file:///c:/Users/Администратор/AvtoTest/src/verification_engine.py).

### 5.2 Remediated Verification Schema
The `verification_records` table was migrated to store full statutory metadata:
```sql
CREATE TABLE verification_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id TEXT NOT NULL,
    legal_act_title TEXT NOT NULL,
    resolution_number TEXT NOT NULL,
    legal_reference TEXT,
    legal_source_url TEXT NOT NULL,
    legal_text_excerpt TEXT,
    proposed_correct_answer TEXT,
    verification_method TEXT NOT NULL,
    verification_status TEXT NOT NULL,
    evidence TEXT,
    verified_at TEXT NOT NULL,
    FOREIGN KEY(question_id) REFERENCES questions(id) ON DELETE CASCADE
);
```

### 5.3 Multilingual Statutory Taxonomy & Precedence
1. **`LEGAL_CONTENT_MATCHED` (9 questions, 0.2%):** Assigned strictly when the question prompt, visual road sign code (Annex 1/2), and proposed correct answer were cross-checked and substantively confirmed against the official regulatory title in Cabinet of Ministers Resolution No. 172.
2. **`LEGAL_REFERENCE_FOUND` (3,138 questions, 52.8%):** Assigned when a specific chapter, clause, annex, or road sign citation is identified in the third-party explanation across Uzbek Latin (`-bob`, `-band`, `-ilova`), Uzbek Cyrillic (`-боб`, `-банд`, `-илова`), or Russian (`глава`, `пункт`, `приложение`, `знак`). Stored with exact Lex.uz URLs ([https://lex.uz/docs/5963102](https://lex.uz/docs/5963102) and [https://lex.uz/ru/docs/5963102](https://lex.uz/ru/docs/5963102)).
3. **`MULTI_SOURCE_CONFIRMED` (206 questions, 3.5%):** Assigned when equivalent questions are independently present in multiple private sources, but lack a specific statutory citation.
4. **`SOURCE_CONFIRMED` (2,592 questions, 43.6%):** Assigned when the question is traceable to a primary source repository without a parsed statutory citation.
5. **`CONFLICT_DETECTED` (0 questions in current working set):** Reserved for active, unresolvable source contradictions.

$$\text{Total Questions Verified} = 9 + 3,138 + 206 + 2,592 = \mathbf{5,945} \text{ questions (100.0%)}$$
The inflation in the master report (claiming 7,473 statuses) is completely eliminated. The `questions.verification_status` column and `verification_records` table match with 100% parity.

---

## 6. Stage 4 — Complete QA Validation

All arbitrary `LIMIT 50` and `LIMIT 200` clauses were permanently removed from [`tests/test_master_database.py`](file:///c:/Users/Администратор/AvtoTest/tests/test_master_database.py). The test suite was expanded to 17 exhaustive test functions.

### 6.1 Pytest Execution Results
```
tests/test_master_database.py::test_database_tables_exist PASSED                   [  5%]
tests/test_master_database.py::test_sqlite_pragmas_pass PASSED                     [ 11%]
tests/test_master_database.py::test_all_questions_have_valid_text_and_encoding PASSED [ 17%]
tests/test_master_database.py::test_all_answers_valid_and_non_empty PASSED         [ 23%]
tests/test_master_database.py::test_every_question_has_valid_options_count PASSED [ 29%]
tests/test_master_database.py::test_exactly_one_correct_answer_per_question PASSED [ 35%]
tests/test_master_database.py::test_detect_and_bound_duplicate_answer_option_text PASSED [ 41%]
tests/test_master_database.py::test_all_1423_images_exist_and_match_sha256 PASSED [ 47%]
tests/test_master_database.py::test_all_1423_images_pillow_readable PASSED        [ 52%]
tests/test_master_database.py::test_unique_image_hashes_in_database PASSED        [ 58%]
tests/test_master_database.py::test_image_question_association_integrity PASSED   [ 64%]
tests/test_master_database.py::test_all_questions_traceable_to_sources PASSED     [ 70%]
tests/test_master_database.py::test_no_duplicate_source_references PASSED         [ 76%]
tests/test_master_database.py::test_retained_source_count_matches_expected_clean_count PASSED [ 82%]
tests/test_master_database.py::test_verification_status_consistency PASSED        [ 88%]
tests/test_master_database.py::test_legal_evidence_completeness_for_verified_questions PASSED [ 94%]
tests/test_master_database.py::test_exports_row_count_and_content_consistency PASSED [100%]

============================= 17 passed in 9.70s ==============================
```

### 6.2 Key Assertions Validated Across the ENTIRE Dataset
* **All 5,945 Questions:** Verified non-empty, length $\ge 5$, no `\ufffd` corruption, valid languages.
* **All 19,472 Answer Options:** Verified non-empty, sequential keys (`A`..`E`), valid binary flags.
* **All 1,423 Image Files:** Verified present on disk, file size $> 100$ B, 100% SHA-256 match, 100% Pillow readable.
* **All 7,383 Clean Source Traces:** Verified zero duplicate records, zero orphaned questions.
* **Deliverables Consistency:** Verified exact row counts across SQLite, JSON, CSV, XLSX, and reports.

---

## 7. Stage 5 — Deliverables Regeneration & Export Parity

Following the successful execution of Stages 1–4, the remediated working database was promoted to production ([master_database.sqlite](file:///c:/Users/Администратор/AvtoTest/master_database.sqlite) and [data/master_database.sqlite](file:///c:/Users/Администратор/AvtoTest/data/master_database.sqlite)). All export deliverables were regenerated via [`src/exporter.py`](file:///c:/Users/Администратор/AvtoTest/src/exporter.py).

### 7.1 Deliverables Manifest
| Deliverable File | File Size | Record Count | Integrity Status |
| :--- | :--- | :--- | :--- |
| [master_database.sqlite](file:///c:/Users/Администратор/AvtoTest/master_database.sqlite) | 18,976,768 bytes | 5,945 questions, 19,472 answers, 7,383 sources | **PASS (100% PRAGMA OK)** |
| [questions.json](file:///c:/Users/Администратор/AvtoTest/questions.json) | 8,767,112 bytes | 5,945 hierarchical JSON objects | **PASS (100% Valid JSON)** |
| [questions.csv](file:///c:/Users/Администратор/AvtoTest/questions.csv) | 3,892,763 bytes | 5,945 tabular rows (UTF-8 BOM) | **PASS (100% Parity)** |
| [questions.xlsx](file:///c:/Users/Администратор/AvtoTest/questions.xlsx) | 1,556,698 bytes | 5,945 formatted spreadsheet rows | **PASS (100% OpenPyXL OK)** |
| [duplicate_report.csv](file:///c:/Users/Администратор/AvtoTest/duplicate_report.csv) | 557,987 bytes | 2,320 conservative comparison pairs | **PASS (100% Parity)** |
| [verification_report.csv](file:///c:/Users/Администратор/AvtoTest/verification_report.csv) | 1,273,431 bytes | 5,945 legal verification audit rows | **PASS (100% Parity)** |
| [source_coverage_report.csv](file:///c:/Users/Администратор/AvtoTest/source_coverage_report.csv) | 344 bytes | 7,383 total clean source records | **PASS (100% Parity)** |
| [source_registry.json](file:///c:/Users/Администратор/AvtoTest/source_registry.json) | 1,543 bytes | 4 source registries | **PASS (100% Parity)** |

---

## 8. Stage 6 — Comparative Forensic Audit & Remaining Issues

### 8.1 Original vs Remediated Metrics Reconciliation
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ORIGINAL VS REMEDIATED COMPARISON                        │
├───────────────────────────────┬──────────────────┬──────────────────────────┤
│ Metric                        │ Pre-Remediation  │ Post-Remediation         │
├───────────────────────────────┼──────────────────┼──────────────────────────┤
│ Total Questions               │ 5,945            │ 5,945 (Zero lost)        │
│ Total Answers                 │ 19,472           │ 19,472 (Zero lost)       │
│ Total Question Images         │ 1,423            │ 1,423 (Zero lost)        │
│ Question Sources Traces       │ 7,689 (306 dupes)│ 7,383 (100% clean)       │
│ Archived Duplicate Traces     │ 0                │ 306 (Fully audited)      │
│ False Visual Conflict Pairs   │ 923              │ 0 (1,379 preserved)      │
│ False Visual Exact Pairs      │ 461              │ 0 (1,379 preserved)      │
│ Verification Statuses Claimed │ 7,473 (inflated) │ 5,945 (Strict parity)    │
│ Automated Pytest Cases        │ 11 (with limits) │ 17 (100% of all data)    │
└───────────────────────────────┴──────────────────┴──────────────────────────┘
```

### 8.2 Catalog of Remaining Findings (Non-Blocking)
1. **Upstream Source Option Typos (9 questions):**
   * Exactly 9 questions in the database contain duplicate answer option texts within the same question (e.g. `UZ-YHQ-622058D7A2`, `UZ-YHQ-637903F345`, `UZ-YHQ-6E0D7C6E92`).
   * Forensic inspection confirmed these errors exist verbatim in the source JSON on `propdd.uz` and `yesprava.uz`. In accordance with Safety Rules 4 and 5, raw source data was preserved intact. These items are cataloged in `tests/test_master_database.py::test_detect_and_bound_duplicate_answer_option_text` for future manual editorial review.
2. **Text-Only Variant Option Subclauses (858 pairs):**
   * 858 pairs of text-only questions share a prompt template (e.g. *"Qayrilish taqiqlanadi:"* / *"U-turn prohibited:"*) but test different regulatory subclauses. They are safely tagged as `POTENTIAL_DUPLICATE_REVIEW` in `duplicate_report.csv` without merging.
3. **Official State Examination Bank Status:**
   * The Traffic Safety Service (DYHXX) of the Ministry of Internal Affairs does not publish an open-data exam repository. The master database represents the highest-quality multi-source curated preparation collection accessible, but cannot be labeled as the state's internal examination software without official documentary licensing.

---

## 9. Rollback Instructions

Should a rollback to the pre-remediation state ever be required:
1. Ensure no active SQLite connections are open.
2. Replace [master_database.sqlite](file:///c:/Users/Администратор/AvtoTest/master_database.sqlite) and [data/master_database.sqlite](file:///c:/Users/Администратор/AvtoTest/data/master_database.sqlite) with the verified snapshot from `backups/forensic_snapshot_pre_remediation/master_database.sqlite`.
3. Restore export files (`questions.json`, `questions.csv`, `questions.xlsx`, `duplicate_report.csv`, `verification_report.csv`, `source_coverage_report.csv`, `source_registry.json`) from `backups/forensic_snapshot_pre_remediation/`.
4. Verify checksums against `backups/forensic_snapshot_pre_remediation/BACKUP_MANIFEST.json`.

---
*End of Controlled Remediation Sprint Report.*
