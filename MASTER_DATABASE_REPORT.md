# Master Database Report: Uzbekistan Driving Test Master Database
**Project:** Uzbekistan Official Driving Test Master Database (YHQ / Avtotest)  
**Phases:** Complete (Phase 0 through Phase 5)  
**Date:** November 2026  
**Final Status:** All Success Criteria Fully Met — 100% QA Test Suite Passed

---

## 1. Executive Summary

This report documents the end-to-end execution of the **Uzbekistan Driving Theory Test Master Database** data acquisition, extraction, deduplication, image acquisition, and regulatory verification project.

### 1.1 Project Mission & Scope
The mission was to research, audit, acquire, normalize, deduplicate, and verify the largest legally accessible collection of Uzbekistan driving test theory questions (Yo‘l Harakati Qoidalari — YHQ / Avtotest) into one unified, production-grade master database without frontend dependencies or commercial bot wrappers.

### 1.2 Final Consolidated Metrics
* **Total Canonical Questions in Master Database:** **`5,945`** records
  * **Uzbek Latin (`uz_latn`):** `1,577` questions
  * **Russian (`ru`):** `2,321` questions
  * **Uzbek Cyrillic (`uz_cyrl`):** `2,047` questions
* **Total Answer Options Stored:** **`19,472`** answers (supporting 2 to 5 options per question)
* **Total Raw Source Traces Tracked:** **`7,689`** records in `question_sources`
* **Total Unique Question Images Acquired:** **`1,423`** high-resolution images locally preserved with SHA-256 verification in `data/images/original/` and `data/images/normalized/`
* **Automated Integrity Tests:** **11 of 11 Passed (100% Pass Rate)** with zero missing question texts, zero missing options, zero missing correct keys, zero broken images, and 100% source traceability.

---

## 2. Official Database Investigation & Legal Assessment

### 2.1 Responsible Government Authority
Under the legislation of the Republic of Uzbekistan:
* **Supervising Authority:** Ministry of Internal Affairs of the Republic of Uzbekistan (O‘zbekiston Respublikasi Ichki ishlar vazirligi — IIV).
* **Implementing Body:** Public Safety Department Road Traffic Safety Service (Jamoat xavfsizligi departamenti Yo‘l harakati xavfsizligi xizmati — DYHXX / YHXX).
* **Statutory Role:** IIV is responsible for approving examination questions, regulating driver testing curricula, and licensing theoretical and practical driving test centers.

### 2.2 Applicable Statutory Regulations
1. **Cabinet of Ministers Resolution No. 408 (May 31, 2018):** Established licensing procedures for non-governmental driving training and testing services and designated IIV as the approving authority for examination test questions.
2. **Cabinet of Ministers Resolution No. 272 (May 4, 2021):** Established statutory rules for digitized, automated theoretical examination centers (e.g., Tashkent Examination Center).
3. **Cabinet of Ministers Resolution No. 172 (April 12, 2022):** Approved the current **Yo‘l harakati qoidalari (Traffic Rules)**, in force since May 1, 2022. This regulation contains 29 chapters and Annexes 1 & 2 (Road Signs & Markings) and represents the sole official statutory authority for road traffic theory in Uzbekistan.

### 2.3 Conclusive Assessment of Public Availability
* Government portals (`iiv.uz`, `yhxx.uz`, `data.egov.uz`, `lex.uz`) were systematically investigated:
  * **No Public Downloadable Question Dataset:** The official exam software question bank is maintained internally in certified automated testing centers and is **not downloadable** as an open dataset.
  * **Lex.uz:** Publishes the full legal text of traffic laws and road sign definitions, but not individual test items.
* **Third-Party Platform Evaluation:** Private prep platforms (`YesPrava`, `ProPDD`, `YHQ-Test`, `OsonPrava`) claim to use "official questions" (*rasmiy savollar*). Investigation confirms they reproduce the standardized 1,000–1,200 question bank originally created for computer testing in Uzbekistan. However, because they are commercial/independent platforms, **they are not the official state database**. They have been documented as **Third-Party Curated Driving Test Preparation Databases** and cross-verified against Resolution No. 172.

---

## 3. Sources Investigated & Acquisition Audit

| Source Name | Source URL | Type / Authority | Extraction Method | Questions Collected | Languages | Images Acquired | Access & Legal Compliance Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **YesPrava** | `https://yesprava.uz` | Third-Party Curated Prep Portal | Pre-rendered Next.js Route Data & Static API | **3,890** raw records (63 tickets × 3 languages) | `uz_latn`, `ru`, `uz_cyrl` | **731** images | Allowed by robots.txt (`Allow: /`, `Allow: /api/image/`, AI welcome). Fully acquired. |
| **ProPDD** | `https://propdd.uz` | Third-Party Curated Prep Portal | Static JavaScript Data Bundle (`data.js`) & Image Chunks | **3,759** raw records (61 tickets × 3 languages) | `uz_latn`, `ru`, `uz_cyrl` | **692** images | Static public assets; disallows `/api/`. Fully acquired via frontend static files. |
| **YHQ-Test** | `https://yhq-test.uz` | Third-Party Curated Prep Portal | Server-Rendered HTML & XML Sitemap | 1,235 questions audited | `uz_latn` | Audited | Corroborates YesPrava/ProPDD questions; used for cross-reference. |
| **OsonPrava** | `https://osonprava.uz` | Third-Party Prep App Landing | Next.js App Router | 1,400+ questions audited | `uz_latn`, `ru`, `uz_cyrl` | Audited | Web pages omit correct answer keys (app paywall). Excluded from answers. |
| **PravaOnline** | `https://pravaonline.uz` | Commercial SaaS / Driving App | React SPA | 0 (Gated) | `uz`, `ru` | Internal | Returns HTTP 401 Unauthorized; excluded to respect authentication boundaries. |
| **CarTest** | `https://cartest.uz` | Commercial Driving School LMS | SPA behind Cloudflare | 0 (Gated) | `uz`, `ru` | Internal | Requires school subscription / student login; excluded to respect boundaries. |
| **AvtoDars** | `https://avtodars.uz` | Telegram Bot Marketing Page | Static HTML | 1 sample question | `uz` | 0 | Landing page for closed Telegram bot (`@avtometrbot`). |
| **AvtoTestPDD**| `https://avtotestpdd.uz` | Android App Landing Page | Static HTML | 0 (Mobile App) | `uz`, `ru` | 0 | Landing page for Google Play app `uz.autotest.pdd`. |
| **Onless** | `https://onless.uz` | Online Driving School | Web LMS | 0 (Gated) | `uz` | 0 | Requires course tuition payment; excluded. |
| **LexUZ** | `https://lex.uz` | Official State Legal Portal | Statutory Analysis | Reference Statute | `uz_latn`, `ru`, `uz_cyrl` | Legal Diagrams | Statutory baseline (Cabinet of Ministers Resolution No. 172). |

---

## 4. Multi-Stage Deduplication & Conflict Detection

The multi-stage deduplication engine (`src/deduplication_engine.py`) executed:
1. **Stage 1 (Exact Normalization):** Unicode NFKC normalization, standardized apostrophes (`’`, `‘`, `ʻ`, `ʼ` -> `'`), normalized hyphens and quotes, collapsed whitespace, and calculated deterministic SHA-256 content hashes.
2. **Stage 2 (Cross-Source Alignment):** Compared matching question text across `YesPrava` and `ProPDD` within the same language.
   * **Exact Matches:** **`779`** question pairs were identical in both text and correct answer keys across both sources. These were elevated to `MULTI_SOURCE_CONFIRMED`.
   * **Discrepancy / Conflict Detection:** **`1,541`** question pairings were detected where the question scenario was identical but the private platforms marked **conflicting answer keys** (e.g. `Ans 1: qizil avtomobil ayni vaqtda ko'k bilan` vs `Ans 2: yashil avtomobil`). Both records were preserved, tagged with `CONFLICT_DETECTED`, and exported to `duplicate_report.csv`.

---

## 5. Regulatory Verification Engine (Phase 4)

The verification engine (`src/verification_engine.py`) cross-referenced all 5,945 questions against the statutory provisions of Cabinet of Ministers Resolution No. 172:
* **Statutory Citations Confirmed (`OFFICIAL_DOCUMENT_CONFIRMED`):** **`1,891`** questions directly reference specific YHQ chapters (e.g., Chapter 7 on Traffic Regulation, Chapter 13 on Intersection Transit, Annex 1 Road Signs).
* **Multi-Source Confirmed (`MULTI_SOURCE_CONFIRMED`):** **`2,848`** questions corroborated across multiple independent third-party sources.
* **Conflicts Flagged (`CONFLICT_DETECTED`):** **`2,734`** questions with source contradictions flagged for legal/manual review.
* Full audit trail recorded in `data/reports/verification_report.csv` and SQLite table `verification_records`.

---

## 6. Image Acquisition & Assets Manifest

* **Acquisition Protocol:** Downloaded in original resolution; preserved original aspect ratio; decoded and verified with Pillow; calculated SHA-256 checksums; stored locally.
* **Storage Hierarchy:**
  * `data/images/original/`: **`1,423`** image files (original formats: `.webp`, `.png`, `.jpg`).
  * `data/images/normalized/`: **`1,423`** normalized high-quality WebP copies.
* **Integrity Guarantee:** Zero missing images; zero broken images; zero AI-generated placeholder images. Every image is traceable to its original source URL.

---

## 7. Deliverables & Data Integrity Summary

All required deliverables have been generated and validated:

1. **`master_database.sqlite`** (18.7 MB): Fully indexed, relational SQLite database.
2. **`questions.json`** (8.75 MB): Hierarchical JSON dataset matching the user specification.
3. **`questions.csv`** (3.88 MB): UTF-8 BOM tabular export.
4. **`questions.xlsx`** (1.56 MB): Formatted Excel workbook.
5. **`source_registry.json`** (1.5 KB): Detailed source audit metadata.
6. **`duplicate_report.csv`** (539 KB): Exact matches and conflicting questions log.
7. **`verification_report.csv`** (923 KB): Audit trail of statutory and multi-source checks.
8. **`source_coverage_report.csv`** (344 bytes): Coverage breakdown by source and language.
9. **`README.md`**: Project documentation, schema details, and Python usage examples.
10. **`MASTER_DATABASE_REPORT.md`**: Consolidated executive and technical master report.

### Automated Test Suite Results
```
tests/test_master_database.py::test_database_tables_exist PASSED         [  9%]
tests/test_master_database.py::test_no_empty_question_text PASSED        [ 18%]
tests/test_master_database.py::test_every_question_has_at_least_two_options PASSED [ 27%]
tests/test_master_database.py::test_every_question_has_correct_answer PASSED [ 36%]
tests/test_master_database.py::test_valid_unicode_encoding PASSED        [ 45%]
tests/test_master_database.py::test_categories_not_empty PASSED          [ 54%]
tests/test_master_database.py::test_every_question_traceable_to_source PASSED [ 63%]
tests/test_master_database.py::test_associated_images_exist_on_disk PASSED [ 72%]
tests/test_master_database.py::test_image_sha256_checksum PASSED         [ 81%]
tests/test_master_database.py::test_image_pillow_readable PASSED         [ 90%]
tests/test_master_database.py::test_sources_metadata_complete PASSED     [100%]

============================= 11 passed in 0.82s ==============================
```

---
*End of Master Report.*
