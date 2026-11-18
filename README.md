# Uzbekistan Official Driving Test Master Database (YHQ / Avtotest)

## 1. Overview & Objective

This project provides the consolidated, verified, and normalized **Master Database of Uzbekistan Driving Licence Theory Examination Questions** (Yo‘l Harakati Qoidalari — YHQ / Avtotest).

It is the result of systematic multi-source data acquisition, deduplication, image asset acquisition, regulatory verification against current statutory traffic regulations (Resolution of the Cabinet of Ministers of the Republic of Uzbekistan No. 172 of April 12, 2022), and automated quality assurance.

### Key Metrics
* **Total Canonical Questions:** `5,945` records across three official testing languages:
  * **Uzbek Latin (`uz_latn`):** `1,577` questions
  * **Russian (`ru`):** `2,321` questions
  * **Uzbek Cyrillic (`uz_cyrl`):** `2,047` questions
* **Total Answer Options:** `19,472` answers (dynamically supporting questions with 2 to 5 options)
* **Total Raw Source Traces:** `7,689` records preserved in `question_sources`
* **Total Associated Images:** `1,423` verified unique high-resolution images stored locally in `data/images/original/` and `data/images/normalized/` with SHA-256 checksums
* **Statutory Verification:** `1,891` questions directly cross-referenced against YHQ chapters/articles; `2,848` confirmed across multiple independent platforms; `2,734` platform discrepancies flagged for review in `duplicate_report.csv`.

---

## 2. Official Authority & Provenance Hierarchy

Per statutory regulations under the **Law of the Republic of Uzbekistan "On Road Traffic Safety"** and **Cabinet of Ministers Resolutions No. 408 (2018) & No. 272 (2021)**:
* **Approving Authority:** Theoretical examination questions are officially approved by the **Ministry of Internal Affairs of the Republic of Uzbekistan (IIV)** and administered through the **Public Safety Department Road Traffic Safety Service (DYHXX / YHXX)**.
* **Open Data Assessment:** The original examination software database is **not publicly downloadable** as open data on government portals (`iiv.uz`, `yhxx.uz`, `data.egov.uz`).
* **Source Provenance:** Third-party preparation platforms (`YesPrava`, `ProPDD`, `YHQ-Test`, `OsonPrava`) publish curated versions of the standardized computerized curriculum (the 1,200+ question bank). The master database preserves complete source traceability to each original platform ticket and position while verifying all answers against official statutory traffic rules (Resolution No. 172).

---

## 3. Deliverables Manifest

| Filename | Format | Description |
| :--- | :--- | :--- |
| **`master_database.sqlite`** | SQLite 3 | Normalized relational database with full schema, foreign keys, and indexes |
| **`questions.json`** | JSON | Machine-readable hierarchical dataset with answers, categories, image links, explanations, and sources |
| **`questions.csv`** | CSV (UTF-8 with BOM) | Tabular export of canonical questions with clean Unicode formatting |
| **`questions.xlsx`** | Excel (XLSX) | Spreadsheet format for human review, filtered by language, category, and verification status |
| **`source_registry.json`** | JSON | Registry of audited platforms, authority levels, access methods, and terms status |
| **`duplicate_report.csv`** | CSV | Detailed log of exact matches, near-duplicates, and answer discrepancies detected across sources |
| **`verification_report.csv`** | CSV | Comprehensive audit trail of statutory citations and regulatory cross-checks |
| **`source_coverage_report.csv`** | CSV | Breakdown of acquired questions and records per source and language |
| **`data/images/`** | WebP / PNG / JPG | Directory containing all 1,423 associated question graphics |

---

## 4. Database Schema

The SQLite database (`master_database.sqlite`) is organized into normalized relational tables:

```
questions               answers                 images
---------               -------                 ------
id (PK, e.g. UZ-YHQ-*)  id (PK)                 id (PK)
canonical_hash (UNIQUE) question_id (FK)        sha256 (UNIQUE)
question_text           option_key (A, B, C...) filename
category_id (FK)        answer_text             original_url
language                is_correct (0 or 1)     local_path
image_id (FK)           sort_order              width, height
explanation                                     file_size
verification_status                             license_status
created_at, updated_at

sources                 question_sources        verification_records
-------                 ----------------        --------------------
id (PK)                 id (PK)                 id (PK)
source_code (UNIQUE)    question_id (FK)        question_id (FK)
source_name             source_id (FK)          verification_method
source_url              original_question_id    verification_result
source_type             original_ticket         evidence
authority_level         original_position       verified_at
access_method           original_url
terms_status            original_language
created_at              raw_payload (JSON)
```

---

## 5. Verification Status Taxonomy

Every question is assigned an objective verification status:
* `OFFICIAL_DOCUMENT_CONFIRMED`: Answer and scenario are corroborated by specific chapter/clause citations from Cabinet of Ministers Resolution No. 172 (YHQ).
* `MULTI_SOURCE_CONFIRMED`: Corroborated across two or more independent preparation databases with identical correct answer keys.
* `SOURCE_CONFIRMED`: Verified from a single primary preparation source.
* `CONFLICT_DETECTED`: Discrepancy detected where different third-party platforms specify different correct answers for the same scenario. Preserved with both variants and flagged for regulatory review.
* `UNVERIFIED`: Imported without cross-source validation.

---

## 6. Usage Examples (Python)

### Querying SQLite
```python
import sqlite3

conn = sqlite3.connect("master_database.sqlite")
cur = conn.cursor()

# Retrieve question with its answer options
qid = "UZ-YHQ-7424EB2B2E"
cur.execute("SELECT question_text, language, explanation FROM questions WHERE id = ?", (qid,))
q_text, lang, expl = cur.fetchone()
print(f"[{lang}] {q_text}")
print(f"Explanation: {expl}")

cur.execute("SELECT option_key, answer_text, is_correct FROM answers WHERE question_id = ? ORDER BY sort_order", (qid,))
for key, text, is_correct in cur.fetchall():
    mark = " [CORRECT]" if is_correct else ""
    print(f"  {key}: {text}{mark}")

conn.close()
```

### Loading JSON
```python
import json

with open("questions.json", "r", encoding="utf-8") as f:
    questions = json.load(f)

print(f"Loaded {len(questions)} canonical questions.")
sample = questions[0]
print(f"Sample Question ID: {sample['id']}")
print(f"Language: {sample['language']}")
print(f"Options Count: {len(sample['answers'])}")
```

---

## 7. Quality Assurance & Automated Testing

The automated test suite verifies all data integrity constraints:
```bash
pytest tests/test_master_database.py -v
```

All 11 tests check:
1. Complete table structure and foreign keys.
2. Zero empty or null question texts.
3. Every question has at least two answer options.
4. Every question has an identified correct answer.
5. Clean Unicode normalization (NFKC).
6. Non-empty categories.
7. 100% source traceability in `question_sources`.
8. Complete local presence of all 1,423 image files.
9. SHA-256 image checksum integrity.
10. Pillow image readability without file corruption.
11. Complete source registry metadata.
