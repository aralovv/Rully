# RULLY 2.0 — MASTER ARCHITECTURAL & PRODUCT TRANSFORMATION BLUEPRINT (REVISION 2.0)

> **Status:** `PHASE 0 — PLANNING & FORENSIC AUDIT (REVISION 2)`  
> **Gate A Status:** **NOT APPROVED — NO SOURCE, CSS, DATABASE, OR DEPLOYMENT FILES HAVE BEEN MODIFIED**  
> **Operating Standard:** Evidence-Driven Principal Engineering · Explicit Fact/Assumption Epistemology · Sub-Gated Production Safety  
> **Deliverable Scope:** Complete revision resolving canonical dataset discrepancies (`1,327` vs `5,945` vs `5,977`), database dependency proofs, sub-gated Phase 1 execution (`1A`–`1F`), bundle versioning/fallback, AI/legal verification governance, SQLite/Turso/Async/Render architectural fixes, and test/release traceability.

---

## EPISTEMOLOGY LEGEND (APPLIED TO EVERY MAJOR CLAIM)

Every claim in this blueprint is explicitly tagged using one of four epistemological labels:
- **`[VERIFIED FACT]`** — Directly observed in this repository's source files, read-only local SQLite queries (`file:master_database.sqlite?mode=ro`), read-only production Turso queries (`SELECT`-only), filesystem metadata, or live browser inspections.
- **`[ASSUMPTION]`** — Reasonable engineering inference or external constraint not yet verified by runtime benchmark or human stakeholder input (e.g., future traffic growth, user willingness to upgrade Render billing).
- **`[PROPOSED DECISION]`** — Recommended target architecture, workflow, or refactoring strategy requiring Gate approval before implementation.
- **`[UNRESOLVED ITEM]`** — Open architectural, legal, budget, or product question that **must not** be guessed and requires explicit human decision before Phase 1+ execution.

---

## PART I — EXECUTIVE SUMMARY & GATE DISCIPLINE

### 1.1 Strategic Mission
- **`[VERIFIED FACT]`** RULLY today operates a production dual-surface Uzbekistan driving-exam platform: a Telegram Bot (`aiogram`), a FastAPI backend + Telegram Mini App Vanilla JS SPA (`static/index.html`, `static/js/*`, `static/css/rully.css`, `527,854 bytes` across `21` files), a FastAPI Admin Financial/Content Control Center (`static/admin/*`), a Telethon MTProto payment listener (`src/mtproto/service.py`), Gemini AI tutoring (`src/ai/gemini_service.py`), and an active `1,327`-question multilingual (`uz_latn`, `uz_cyrl`, `ru`) canonical catalog partitioned into `67` deterministic Bilet tickets (`66 × 20 + 7`).
- **`[VERIFIED FACT]`** Infrastructure currently spans **Vercel** (`https://rully-three.vercel.app`, region `bom1`, Python serverless `api/index.py` + static routes), **Render** (`https://rully-app.onrender.com`, `render.yaml` `plan: free`, `singapore`, all-in-one Web Service running API + Bot + MTProto + 15m order expiration + 12h scraper + 7m keepalive pinger), and **Turso** (`https://rully-aralovv.aws-ap-south-1.turso.io`, libSQL cloud DB over HTTP).
- **`[PROPOSED DECISION]`** Transform RULLY 2.0 across Phases `1`–`8` from an engineering-first prototype with legacy ETL weight and fragile multi-worker coupling into a high-trust, high-speed, cockpit-inspired flagship driving mastery product benchmarking against inspected patterns from [`bilet.run`](https://bilet.run/), without sacrificing data integrity, test fidelity, or cost discipline.

### 1.2 Hard Gate Rules (Phase 0 -> Phase 8)
- **`[PROPOSED DECISION]`** No code edit, schema DDL/DML, test modification, or deployment may cross a phase boundary without explicit human sign-off at that gate:
  - **Gate A (Current):** Approve this revised Blueprint + choose options for Unresolved Items (`U-01`..`U-07`).
  - **Phase 1 Independent Sub-Gates (`1A` -> `1B` -> `1C` -> `1D` -> `1E` -> `1F`):** Database inventory, backup & restore proof, isolated archive prototype, Turso/SQLite parity, curriculum legal/explanation review, and separate explicit approval before any production Turso write.
  - **Gates B–H (Phases 2–8):** Sequential engineering gates covering Sync/Admin reliability, Design System & Cockpit UI (`Phases 3–4`), SM-2 Spaced Repetition & Curriculum Expansion (`Phase 5`), Bot/AI/Payment resilience (`Phase 6`), Security/Performance/Observability (`Phase 7`), and Production Release/Rollback (`Phase 8`).

---

## PART II — DISCREPANCY & ASSUMPTIONS REGISTER

### 2.1 Master Discrepancy Register

| ID | Discrepancy / Risk | Tag | Evidence / Root Cause | Impact & Required Resolution |
| :--- | :--- | :--- | :--- | :--- |
| **`D-01`** | Canonical count reported as `1,327` vs older audits citing `5,945` or `5,977` | `[VERIFIED FACT]` | `5,945` = pre-unification per-language `questions` rows (`questions.json` / `verification_records`); `5,977` = `5,945 + 32` `CQ-*` rows inserted by `StagingManager.approve_question()` solely to satisfy `question_sources.question_id -> questions.id` FK; `1,327` = deduplicated multilingual `canonical_questions` (`1,295 CANON-YHQ-*` + `32 CQ-1296..CQ-1327`) holding `3,981` translations (`1,327 × 3`). | Reconciled completely in Section III. `1,327` is 100% of the active bank. Never merge or delete without resolving FK dependencies (`D-03`). |
| **`D-02`** | Local SQLite (`master_database.sqlite`) vs Production Turso schema and row drift | `[VERIFIED FACT]` | Local DB has `44` tables (including `user_ticket_progress` + `sqlite_sequence`), `audit_merge_log = 1,301` (`ADMIN_AMENDMENT_APPROVAL: 6`, `0 ADMIN_STAGING_APPROVAL`), `telegram_users: 1`, `exam_results: 3`, `ai_conversations: 0`. Production Turso has `42` user tables + `sqlite_sequence` (**missing `user_ticket_progress`!**), `audit_merge_log = 1,339` (`ADMIN_STAGING_APPROVAL: 32`, `ADMIN_AMENDMENT_APPROVAL: 12`), and live production rows (`telegram_users: 5`, `exam_results: 31`, `ai_conversations: 157`, `payment_orders: 6`, `payment_transactions: 4`, `unmatched_payments: 3`). | Live `get_learning_analytics` / `get_ticket_progress_map` queries `user_ticket_progress` on Turso where the table doesn't exist until lazily created (silently catching creation errors in `_ensure_ticket_progress_table`). Local DB is stale for user/audit rows and must **never** overwrite Turso. Fixed in Sub-Gate `1D`. |
| **`D-03`** | Naive "archive separation" breaks active sync, exporter, and pytest suite | `[VERIFIED FACT]` | `src/sync/diff_detector.py`, `src/sync/incremental_unifier.py`, `src/sync/staging_manager.py`, `src/sync/service.py`, `src/exporter.py`, `tests/test_master_database.py`, `tests/test_question_sync.py`, and `tests/test_unified_product.py` actively query/mutate `questions`, `answers`, `sources`, `question_sources`, `verification_records`, and `audit_merge_log`. | Only `archived_duplicate_source_traces` (`306`) and `proposed_source_trace_cleanup` (`306`) have zero code references. Removing `questions`/`answers`/`verification_records`/`question_sources` requires refactoring sync FK traces + test fixtures first (Section IV). |
| **`D-04`** | `32` `CQ-1296..CQ-1327` questions lack `legal_reference`; `107..114` translations lack `explanation` | `[VERIFIED FACT]` | `StagingManager.approve_question()` hardcodes `legal_reference = NULL, legal_act_title = 'Cabinet of Ministers Resolution No. 172'` (`src/sync/staging_manager.py:330`). Across `canonical_translations`, missing `explanation` counts are `107` (`uz_latn` = `100 CANON + 7 CQ`), `112` (`uz_cyrl` = `105 CANON + 7 CQ`), `114` (`ru` = `107 CANON + 7 CQ`). | Addressed in Sub-Gate `1E` with strict human/legal provenance (Section VI). AI output must never auto-mark legal references as verified. |
| **`D-05`** | `TursoConnection.commit()` and `.rollback()` are no-ops (`pass`) | `[VERIFIED FACT]` | `src/db_adapter.py:235-239`. Each `cur.execute()` executes as an immediate autocommitted HTTP request on Turso unless sent inside `execute_batch()` (`_client.batch()`). | Multi-step mutations (`StagingManager.approve_question`) are non-atomic on Turso and can leave partial state if step 4 or 6 fails. Also `IncrementalUnifier` (`src/sync/incremental_unifier.py:65`) uses raw `sqlite3.connect(self.db_path)` instead of `get_db_connection()`, bypassing Turso! |
| **`D-06`** | `PRAGMA foreign_keys = ON` not enforced on Turso or raw `sqlite3.connect` callers | `[VERIFIED FACT]` | `get_db_connection()` sets `PRAGMA foreign_keys = ON` only for local SQLite (`src/db_adapter.py:272`). Raw `sqlite3.connect` calls in `tests/`, `avtotest_product.py`, `incremental_unifier.py`, and default `master_database.sqlite` metadata report `PRAGMA foreign_keys` default = `0`. | Require uniform per-connection FK pragma wrapper + strict `batch()` FK behavior verification on Turso in Sub-Gate `1D`. |
| **`D-07`** | Legacy `tests/test_master_database.py` verifies frozen pre-sync CSV/JSON deliverables | `[VERIFIED FACT]` | Checks exact equality `questions.json == 5945`, `questions.csv == 5945`, `questions.xlsx == 5945`, `verification_report.csv == 5945`, `source_coverage_report.csv sum == 7383`, and `answers` `9` raw duplicate text defects. | Deleting/weakening these tests violates Release Governance. Plan preserves coverage via `archive_etl.sqlite` or explicit test suite separation (Section IX). |
| **`D-08`** | Blueprint v1 mixed SM-2 into Phase 1 and conflated catalog parse with Vercel cold start | `[VERIFIED FACT]` | Critique findings #4, #6, #7; `render.yaml:6` uses `plan: free` (`1` web service, no paid worker service); Vercel cold start includes Python ASGI + `libsql_client` + Turso TLS RTT, not just JSON parse. | Fixed in Sections V, VII, and VIII. SM-2 strictly moved to Phase 5; worker split framed against Render `$0/mo` vs `$7+/mo` budget. |

### 2.2 Explicit Assumptions Register

- **`[ASSUMPTION A-01]`:** Legal applicability of **Cabinet of Ministers Resolution No. 172 (April 12, 2022, `lex.uz/docs/5963102`)** covers core Uzbekistan traffic rules, road signs, and markings, while medical first-aid or vehicle maintenance questions may reference clinical first-aid protocols or technical inspection annexes rather than YHQ Chapters `1–29`. Verification rules must support non-VMQ-172 classifications instead of forcing fake citations.
- **`[ASSUMPTION A-02]`:** Primary users access RULLY on budget-to-midrange Android/iOS mobile devices inside the Telegram Mini App WebView over variable 3G/4G networks in Uzbekistan. Asset payloads (`static/` + images + API JSON) must remain lightweight.
- **`[ASSUMPTION A-03]`:** Existing user financial records (`payment_orders`, `payment_transactions`, `user_subscriptions`, `unmatched_payments`), `telegram_users`, `user_sessions`, `exam_results`, and `mtproto_accounts` on production Turso constitute live customer state with **zero tolerance for data loss**.
- **`[ASSUMPTION A-04]`:** The repository currently runs on `plan: free` on Render (`render.yaml:6`) and Hobby/Standard limits on Vercel (`vercel.json` `maxDuration: 60`) with no pre-authorized budget increase for additional paid Render worker instances unless explicitly approved in Decision `U-03`.

---

## PART III — CANONICAL DATASET RECONCILIATION & SQL EVIDENCE

> **Verdict (`[VERIFIED FACT]`):** **`1,327` is 100% of the complete active multilingual RULLY question bank.** `5,945` and `5,977` are **not** missing questions — they represent the pre-deduplication, per-language source-row schema (`questions` table, where Uzbek Latin, Uzbek Cyrillic, and Russian versions of the same question from `yesprava` and `propdd` were stored as separate rows).

### 3.1 Exact Reconciliation Across All Stores (SQL Evidence)

Measured read-only on `master_database.sqlite` (`25.21 MB`, `44` tables, `34` indexes, `29` declared FKs) and production Turso (`SELECT`-only, `42` user tables + `sqlite_sequence`):

| Metric / Entity | Local SQLite Count | Production Turso Count | Exact Mathematical Meaning (`[VERIFIED FACT]`) |
| :--- | :---: | :---: | :--- |
| **`canonical_questions`** | **`1,327`** | **`1,327`** | **Complete active bank:** `1,295` (`CANON-YHQ-0001`..`1295`) + `32` (`CQ-1296`..`CQ-1327`). |
| — `CANON-YHQ-*` breakdown | `1,295` | `1,295` | `1,139` exact duplicates (`EXACT_DUPLICATE`) + `14` semantic duplicates (`SEMANTIC_DUPLICATE`) + `82` YesPrava-only (`ADD_UNIQUE_YESPRAVA`) + `60` ProPDD-only (`ADD_UNIQUE_PROPDD`). Total = `1139 + 14 + 82 + 60 = 1,295`. |
| — `CQ-*` breakdown | `32` | `32` | `CQ-1296`..`CQ-1327` published from `staged_questions` human-in-the-loop approvals (`ADMIN_MANUALLY_APPROVED`). |
| **`canonical_translations`** | **`3,981`** | **`3,981`** | `1,327 × 3 = 3,981` (`1,327 uz_latn`, `1,327 uz_cyrl`, `1,327 ru` — zero missing language rows). |
| **`canonical_answers`** | **`4,349`** | **`4,349`** | Unified trilingual options (`text_uz_latn`, `text_uz_cyrl`, `text_ru`) across all `1,327` canonical items. |
| **`questions` (legacy table)** | **`5,977`** | **`5,977`** | `5,945` baseline extracted per-language questions (`ru: 2,321`, `uz_cyrl: 2,047`, `uz_latn: 1,577`) **plus** `32` `CQ-*` synthetic parent rows (`uz_latn`) inserted by `StagingManager.approve_question()` to satisfy `question_sources.question_id -> questions.id` FK (`1,577 + 32 = 1,609 uz_latn`; total `2,321 + 2,047 + 1,609 = 5,977`). |
| **`verification_records`** | **`5,945`** | **`5,945`** | `1:1` verification records for the `5,945` pre-sync `questions` rows (`LEGAL_REFERENCE_FOUND: 3,138`, `SOURCE_CONFIRMED: 2,592`, `MULTI_SOURCE_CONFIRMED: 206`, `LEGAL_CONTENT_MATCHED: 9`). Left-joining `questions` shows **`32` rows with `vr.id IS NULL` — 100% of them are `CQ-1296..CQ-1327` (`5,977 - 5,945 = 32`)**. |
| **`answers` (legacy table)** | **`19,579`** | **`19,579`** | Per-language option rows belonging to the legacy `5,977` `questions` table. |
| **`question_sources`** | **`7,415`** | **`7,415`** | Raw scraped payloads & slot traces: `propdd` (`ru: 1,213`, `uz_cyrl: 1,213`, `uz_latn: 1,213` = `3,639`) + `yesprava` (`ru: 1,248`, `uz_cyrl: 1,248`, `uz_latn: 1,280` = `3,776`). Note `7,415 - 7,383 = 32` (`CQ-*` source rows!). |
| **`staged_questions`** | **`70`** | **`70`** | All `70` have `review_status = 'APPROVED'`, mapping to `38` distinct `published_canonical_id` values (`52` rows mapped to `32 CQ-*` IDs; `18` rows mapped to `6 CANON-*` amendment updates). |
| **`audit_merge_log`** | **`1,301`** | **`1,339`** | **Drift (`+38` on Turso):** Local has `1,295` initial merges + `6 ADMIN_AMENDMENT_APPROVAL`. Turso has `1,295` initial merges + `32 ADMIN_STAGING_APPROVAL` + `12 ADMIN_AMENDMENT_APPROVAL` = `1,339`. |
| **`images` / `categories`** | `1,447` / `42` | `1,447` / `42` | `782` canonical questions have `has_image = 1`; all `42` categories map to both canonical & legacy sets. |
| **Live App / Financial Tables** | Stale Dev | Live Prod | Turso holds `telegram_users: 5`, `exam_results: 31`, `session_answers: 125`, `user_mistakes: 70`, `user_bookmarks: 10`, `user_sessions: 47`, `user_subscriptions: 10`, `payment_orders: 6`, `payment_events: 7`, `payment_transactions: 4`, `unmatched_payments: 3`, `ai_conversations: 157`, `ai_usage_limits: 11`, `admin_users: 2`. Turso **lacks** `user_ticket_progress`! |

### 3.2 How `5,945` Compressed Cleanly Into `1,295` Canonical Entities (`src/unification_engine.py`)
1. **`[VERIFIED FACT]`** Raw extraction pulled `2` sites × `3` languages (`~1,205`–`1,269` questions per site-language pair) into separate rows in `questions` (`5,945` total before incremental staging). Notice why `yesprava` alone had `~1,240` questions per language (`× 3 ≈ 3,720`) plus `propdd` (`~1,205 × 3 = 3,615`), with cross-source deduplication collapsing `propdd + yesprava` identical items in `src/unification_engine.py` into **one canonical ID** containing all 3 translations (`canonical_translations`) and trilingual options (`canonical_answers`).
2. **`[VERIFIED FACT]`** Resulting `canonical_questions` providers breakdown:
   - `["propdd", "yesprava"]`: **`1,153`** (`1,139 EXACT_DUPLICATE` + `14 SEMANTIC_DUPLICATE`)
   - `["yesprava"]`: **`82`** (`ADD_UNIQUE_YESPRAVA`)
   - `["propdd"]`: **`60`** (`ADD_UNIQUE_PROPDD`)
   - `"YESPRAVA"` (staged later via `StagingManager`): **`32`** (`CQ-1296`..`CQ-1327`)
   - **Grand Total: `1,153 + 82 + 60 + 32 = 1,327`**.

### 3.3 Reconciliation Against the 67 Official Bilet Tickets & All Code Paths
- **`[VERIFIED FACT]`** Every question-selection and exam-generation code path across both FastAPI and Telegram Bot queries **exclusively** `canonical_questions` / `canonical_translations` / `canonical_answers`:
  1. `src/avtotest_product.py` (`AvtotestProductEngine._preload_cache()`): Loads all `1,327` `canonical_questions`, `3,981` `canonical_translations`, and `4,349` `canonical_answers` ordered by `canonical_id`.
     - `create_exam_session()` samples `20` from `self._all_canonical_ids` (`1,327`).
     - `get_tickets_summary()` & `get_ticket_question_ids(n)` slice `_ordered_all_ids()` (`1,327`) into `TICKET_SIZE = 20`: **Tickets `1..66` (`20` questions each = `1,320`) + Ticket `67` (`7` questions) = `1,327` (`100%` bank coverage, verified by `tests/test_rully_2_architecture.py:44-62`)**.
     - `get_questions_by_category()`, `get_random_practice()`, `get_adaptive_question_ids()`, `get_question()` all operate strictly on `_cache_questions` / `canonical_questions`.
  2. `src/api/routes_theory.py`: `/api/categories`, `/api/questions/{canonical_id}`, `/api/session/start` (`EXAM`, `CATEGORY`, `RANDOM`, `MISTAKES`, `CUSTOM`, `BILET`, `ADAPTIVE`) delegate strictly to `AvtotestProductEngine` and `BotDatabase`.
  3. `src/bot/handlers/practice.py` & `src/bot/handlers/custom_test.py`: Quick test, category test, and custom count directly execute `SELECT canonical_id FROM canonical_questions ...` and render via `AvtotestProductEngine`.
  4. `src/ai/gemini_service.py` & `src/ai/tools.py`: AI lookups query `canonical_questions` joined with `canonical_translations`, `canonical_answers`, `user_bookmarks`, `user_mistakes`.

### 3.4 Storage Footprint Justification (`25.21 MB` Local SQLite)
Measured approximate payload sizes (`LENGTH(CAST(col AS BLOB))` sum, excluding B-tree/index/WAL overhead):
- **Legacy ETL / Extraction Tables (~`14.85 MB` raw row payload + indexes):**
  - `question_sources` (`7,415` rows): `7,798,950 bytes` (`~7.80 MB` due to `raw_payload` JSON blobs)
  - `verification_records` (`5,945` rows): `2,936,338 bytes` (`~2.94 MB`)
  - `questions` (`5,977` rows): `2,492,627 bytes` (`~2.49 MB`)
  - `answers` (`19,579` rows): `1,619,802 bytes` (`~1.62 MB`)
- **Snapshot Cleanup Tables (~`0.33 MB`):** `archived_duplicate_source_traces` (`306` rows, `303,738 bytes`), `proposed_source_trace_cleanup` (`306` rows, `23,923 bytes`).
- **Active Canonical Catalog (~`3.52 MB`):** `canonical_translations` (`1,548,986 bytes`), `canonical_answers` (`813,595 bytes`), `canonical_questions` (`760,983 bytes`), `images` (`391,617 bytes`).

---

## PART IV — DATABASE DEPENDENCY MAP & ARCHIVE SEPARATION SAFETY PROOF

> **Critical Engineering Proof (`[VERIFIED FACT]`):** Moving all "archival" tables out of `master_database.sqlite` in one step is **UNSAFE** under the current codebase. Below is the complete dependency proof showing what is safe immediately vs what requires coordinated refactoring.

### 4.1 Complete Archival Candidate Dependency Matrix

| Table | Rows | Incoming FKs | Outgoing FKs | Python Code Referencers (`[VERIFIED FACT]`) | API / Admin / Sync Impact | Test Impact (`tests/`) | Safe Immediate Archive? |
| :--- | :---: | :--- | :--- | :--- | :--- | :--- | :---: |
| **`archived_duplicate_source_traces`** | `306` | **None** | **None** | **ZERO references** anywhere in `src/`, `api/`, `scripts/`, `tests/` | Zero runtime/admin impact | Zero test impact | **YES** (Zero dependencies) |
| **`proposed_source_trace_cleanup`** | `306` | **None** | **None** | **ZERO references** anywhere in `src/`, `api/`, `scripts/`, `tests/` | Zero runtime/admin impact | Zero test impact | **YES** (Zero dependencies) |
| **`verification_records`** | `5,945` | **None** | `question_id -> questions.id (CASCADE)` | `src/verification_engine.py`, `src/unification_engine.py`, `src/database.py` | Offline/batch only; NOT used by live API/Bot/Sync | `tests/test_master_database.py` (`required_tables`, `vr` consistency, `lex.uz` checks) | **ONLY WITH TEST PLAN** (`archive_etl.sqlite` target or RFC) |
| **`answers`** | `19,579` | **None** | `question_id -> questions.id (CASCADE)` | `src/sync/diff_detector.py:159`, `src/exporter.py:91`, `unification_engine.py`, `deduplication_engine.py`, `acquire_all.py`, extractors | **`DiffDetector` joins `answers`** during scheduled 12h/admin sync checks! | `tests/test_master_database.py` (counts `>= 19472`, `9` duplicate options check) | **NO** until `DiffDetector` queries `canonical_answers` |
| **`questions`** | `5,977` | `answers(CASCADE)`, `question_sources(CASCADE)`, `verification_records(CASCADE)` | `image_id -> images.id`, `category_id -> categories.id` | **`DiffDetector` (`canonical_hash`, `JOIN`)**, **`StagingManager.approve_question` (`INSERT OR IGNORE INTO questions` FK shim!)**, `Exporter`, `unification_engine.py`, `acquire_all.py`, extractors | **Breaks Sync (`sync/check`), Admin Staging Approval (`staging/*/approve`), and `test_question_sync.py`** if dropped before refactor! | `tests/test_master_database.py` & `tests/test_question_sync.py` | **NO** until Sync & Staging FK decouple from `questions.id` |
| **`question_sources`** | `7,415` | **None** | `question_id -> questions.id (CASCADE)`, `source_id -> sources.id` | **`DiffDetector` (`max_ticket`, known slots)**, **`StagingManager.stage_diff_items` & `approve_question`**, **`IncrementalUnifier`**, **`QuestionSyncService.get_database_metrics` (`COUNT(DISTINCT original_ticket)`)**, `Exporter` | **Breaks Admin Sync Status widget**, periodic 12h sync, and duplicate prevention during staging! | `tests/test_master_database.py` (`>= 7383`), `tests/test_question_sync.py` | **NO — KEEP IN RUNTIME OR MIGRATE TO `canonical_source_links`** |
| **`sources`** | `4` | `question_sources.source_id` | **None** | `DiffDetector`, `StagingManager`, `Exporter`, `database.py`, extractors | Breaks sync adapter ID lookup (`source_code -> id`) | `tests/test_master_database.py` (`required_tables`) | **NO — KEEP IN RUNTIME DB** (`4` rows, `660 bytes`) |
| **`audit_merge_log`** | `1,301` / `1,339` | **None** | `canonical_id -> canonical_questions.canonical_id (CASCADE)` | `StagingManager.approve_question` (`ADMIN_STAGING_APPROVAL`), `IncrementalUnifier`, `unification_engine.py` | Audit provenance log for every canonical ID; tiny footprint (`~205 KB`) | `tests/test_unified_product.py:149` (`>= 1295`), `tests/test_question_sync.py` | **NO — KEEP IN RUNTIME DB** (active audit log) |
| **`staged_questions`** | `70` | **None** | `staged_image_id -> images.id` | `StagingManager`, `routes_admin_questions.py` | Active Admin Moderation Queue | `tests/test_question_sync.py` | **NO — MUST STAY IN RUNTIME DB** |

### 4.2 Safe Archive Separation Architecture (`[PROPOSED DECISION]`)

Because `PRAGMA foreign_keys` is disabled by default on naive connections (`0`) and Turso does not support cross-database `ATTACH` joins across remote HTTP databases (`libsql-client`), cross-DB foreign keys cannot exist cleanly between `master` and `archive`. Therefore:

1. **Tier 0 (Immediate Zero-Risk Archive in Sub-Gate `1C`):**
   - Archive `archived_duplicate_source_traces` (`306` rows) and `proposed_source_trace_cleanup` (`306` rows) to `data/archive/rully_etl_archive.sqlite` (SHA-256 verified) after Sub-Gate `1B` backup & restore passes. Zero code changes needed.
2. **Tier 1 (Clean Runtime Separation — Refactor First, Never Drop Blindly):**
   - **Pre-requisite Code Refactor (in Sub-Gate `1C` local prototype BEFORE touching DB):**
     1. Add lightweight active provenance columns/table `canonical_source_links` (or migrate `question_sources.canonical_id -> canonical_questions.canonical_id` WITHOUT storing megabyte `raw_payload` JSON blobs on every row; move historical `raw_payload` blobs to archive!).
     2. Refactor `DiffDetector` (`src/sync/diff_detector.py`) to compute `canonical_hash` from `canonical_questions` + `canonical_translations` + `canonical_answers` and check `canonical_answers.is_correct` instead of joining legacy `questions`/`answers`.
     3. Refactor `StagingManager.approve_question` (`src/sync/staging_manager.py:378-396`) and `IncrementalUnifier` (`src/sync/incremental_unifier.py:177-184`) to stop inserting dummy rows into legacy `questions`.
   - **What Stays in Live Runtime DB (Turso + App SQLite):** `canonical_questions`, `canonical_translations`, `canonical_answers`, `categories`, `images`, `sources`, `audit_merge_log`, `staged_questions`, pruned `canonical_source_links` (no multi-MB `raw_payload` JSON blobs), plus all user/session/ticket/payment/AI/admin tables.
   - **What Moves to `data/archive/rully_etl_archive.sqlite` (Read-Only Historical ETL Store):** `questions` (`5,977`), `answers` (`19,579`), `verification_records` (`5,945`), legacy full `question_sources` with `raw_payload` blobs (`7,415`), `archived_duplicate_source_traces` (`306`), `proposed_source_trace_cleanup` (`306`). Net runtime DB reduction: **`~14–15 MB` (~60–75% of catalog DB payload)**.
   - **Test Suite Preservation Rule:** `tests/test_master_database.py` continues executing without relaxation or deletion by pointing its read-only ETL verification fixture to `data/archive/rully_etl_archive.sqlite` (only after explicit Gate 1C/1F user approval — see `[UNRESOLVED ITEM U-01]`).

---

## PART V — PHASE 1 DETAILED SUB-GATES & PRODUCTION DATA SAFETY PROTOCOL

> **Hard Safety Rule (`[PROPOSED DECISION]`):** Phase 1 contains **zero SM-2 feature work** (moved strictly to Phase 5). Every Phase 1 sub-gate (`1A` through `1F`) requires its own explicit verification artifact and human approval before the next mutating step runs.

### 5.1 Sub-Gate Breakdown (`1A`–`1F`)

| Sub-Gate | Scope & Actions | Output Artifacts | Pass / Exit Criteria | Human Sign-Off Required? |
| :---: | :--- | :--- | :--- | :---: |
| **`1A`** | **Read-Only Inventory & Dependency Mapping.** Run non-mutating SQLite (`?mode=ro`) & Turso (`SELECT`-only) forensic scripts; finalize FK graph, `sqlite_master` DDL diff, row counts, null/missing quality list, and Turso vs local schema delta (`user_ticket_progress` gap, `audit_merge_log` `+38` diff). | `docs/audit/1A_inventory.json`, DDL diff report | 100% tables, indexes, triggers, FKs, and Python readers mapped with zero DB writes. | Yes (Done conceptually here; formal artifact run in 1A) |
| **`1B`** | **Backup Creation, SHA-256 Verification & Actual Restore Test.** Export bit-for-bit SQLite backup (`sqlite3 .backup` API, NEVER raw `shutil.copy2` while WAL active!) + complete logical SQL + JSON dump from production Turso (`SELECT`-only). Compute `.sha256` manifests. **Actually restore** both backups into ephemeral temp DBs and run integrity/row-count assertions! | `data/backups/prod_turso_dump_<ts>.sql`, `data/backups/local_pre_p1_<ts>.sqlite`, `.sha256` manifest, `1B_restore_verification.log` | `PRAGMA integrity_check == 'ok'`; restored table counts match source 100% (`telegram_users=5`, `payment_orders=6`, `canonical_questions=1327`, `ai_conversations=157`, etc.). | **MANDATORY** |
| **`1C`** | **Local Isolated Archive-Separation Prototype.** On an isolated copy `tmp/proto_runtime.sqlite` + `tmp/proto_archive.sqlite`: implement Tier 0 cleanup + Tier 1 code refactor (`DiffDetector`, `StagingManager`, `IncrementalUnifier`, `Exporter`) with `PRAGMA foreign_keys = ON`. Verify full `pytest` suite (including staging approve/reject, exam generation, and archive ETL tests). | Prototype diff PR/patch, test pass log, byte-size reduction metrics | `PRAGMA foreign_key_check == []`, `PRAGMA integrity_check == 'ok'`, zero regressions across all test modules, staging/sync round-trip passes. | **MANDATORY** |
| **`1D`** | **SQLite / Turso Migration Parity & Transaction Testing.** Align missing Turso schema (`user_ticket_progress` + indexes), replace multi-step cursor writes in `StagingManager` & `IncrementalUnifier` with atomic `execute_batch()`, add per-connection `PRAGMA foreign_keys = ON` behavior test, and test migrations against a scratch/staging Turso branch (not prod!). | `src/db_adapter.py` dialect matrix, staging Turso test log | 100% schema parity (`sqlite_master` tables & columns match between local SQLite and staging Turso), atomic rollback simulation leaves 0 orphan rows. | **MANDATORY** |
| **`1E`** | **Curriculum Explanation & Legal-Reference Quality Remediation.** Audit all `32` `CQ-1296..CQ-1327` missing `legal_reference` and all `100–114` translations missing `explanation`. Implement legal provenance columns & editorial workflow (Section VI). Any AI-assisted draft remains `DRAFT_NEEDS_REVIEW` until human legal check. | `1E_content_quality_report.json`, editorial CSV/UI queue | Zero fabricated `lex.uz` citations; all `1,327` questions carry an explicit verified provenance status (`VERIFIED_*` or `UNRESOLVED_LEGAL_REVIEW`); all 3 scripts parity-checked for completed items. | **MANDATORY** |
| **`1F`** | **Production Migration Readiness Review.** Pre-flight checklist verifying backups (<24h old, restore-tested), idempotent migration scripts, rollback script tested on Turso staging, maintenance window/read-only mode plan, and post-migration smoke probes. | `1F_prod_readiness_signoff.md` | **EXPLICIT SEPARATE HUMAN APPROVAL** granted specifically for the production maintenance window. **ZERO production Turso writes prior to 1F approval.** | **STRICT EXPLICIT PROD APPROVAL** |

### 5.2 Production Data Safety Protocol
1. **`[PROPOSED DECISION]` Snapshot Before Copy (`sqlite3.Connection.backup`):** Never copy a live SQLite database with `shutil.copy2` while WAL mode is active (`-wal` / `-shm` frames can be omitted, corrupting point-in-time state — e.g. existing `IncrementalUnifier.create_database_backup()` on line 31 uses `shutil.copy2`!). Always use `src_conn.backup(dst_conn)`.
2. **`[PROPOSED DECISION]` Immutable Production-First Principle:** Live `telegram_users`, `payment_orders`, `payment_transactions`, `user_subscriptions`, `user_sessions`, `exam_results`, `ai_conversations`, and `mtproto_accounts` reside **only in production Turso**. Local SQLite is never pushed upward to overwrite Turso transactional tables; schema/catalog updates run via idempotent, forward-only DDL/DML scripts keyed on `canonical_id` or `staged_id`.
3. **`[PROPOSED DECISION]` Safe Sync Lock (`maintenance_mode` / Idempotency):** During Sub-Gate `1F` Turso DDL/archive migration, temporarily pause automated Render sync jobs, verify HTTP write routes handle transient retries, execute batched DDL/DML atomically, and verify `rowcount` + `PRAGMA foreign_key_check` equivalent before reopening writes.

---

## PART VI — `canonical_bundle.json` CONSISTENCY, VERSIONING & FALLBACK ARCHITECTURE

> **Context (`[VERIFIED FACT]`):** Currently `src/export_canonical.py` generates `data/canonical_questions.json` (`5,609,122 bytes`), which is **excluded** from Vercel deployments by `.vercelignore:26` (`data/canonical_questions.json`), while `AvtotestProductEngine._get_connection()` (`src/avtotest_product.py:89-93`) queries local SQLite if present or Turso over HTTP on Vercel cold start (`SELECT canonical_questions` + `canonical_translations` + `canonical_answers`). No versioned, checksummed `canonical_bundle.json` exists yet!

### 6.1 Target `canonical_bundle.json` Specification (`[PROPOSED DECISION]`)

If RULLY adopts a static/artifact `canonical_bundle.json` in Phase 2/3 to eliminate full-table Turso downloads on serverless boot and allow fast client/API bootstrapping, it **MUST** implement the following complete lifecycle:

1. **Deterministic Schema & Cryptographic Integrity Envelope:**
   ```json
   {
     "schema_version": 2,
     "bundle_version": "2026.11.27T010000Z-r1327",
     "db_catalog_revision": 42,
     "generated_at": "2026-11-27T01:00:00Z",
     "canonical_count": 1327,
     "translation_count": 3981,
     "answer_count": 4349,
     "payload_sha256": "<sha256 of canonical UTF-8 sorted-keys JSON array>",
     "questions": [ ... ],
     "categories": [ ... ]
   }
   ```
   - Companion detached signature/manifest file (`canonical_bundle.manifest.json`) holding `bundle_version`, `db_catalog_revision`, `payload_sha256`, `byte_length`, and per-image `sha256` references.
2. **Atomic Generation & Replacement:**
   - Exporter writes to `canonical_bundle.json.tmp.<pid>`, calls `f.flush(); os.fsync(f.fileno())`, verifies JSON re-parse + SHA-256 + `canonical_count >= 1295`, and atomically swaps via `os.replace(tmp_path, target_path)`. Partial reads are impossible.
3. **Database-to-Bundle Drift Detection (`db_catalog_revision`):**
   - Add a `catalog_version` row in `system_settings` (`INTEGER`, incremented transactionally whenever any `StagingManager` approval, `edit`, or curriculum script modifies `canonical_*` or `categories`).
   - On server startup (or every `300s` TTL check), API compares `bundle.db_catalog_revision` vs lightweight `SELECT setting_value FROM system_settings WHERE setting_key='catalog_version'` (`~10ms` single-row Turso query, NOT downloading 5.6 MB!).
4. **Admin Edit Invalidation & Vercel Deploy Sync:**
   - When an Admin approves/edits a question on Render Admin Panel:
     1. Increment `system_settings.catalog_version` inside the same Turso `execute_batch()`.
     2. Invalidate local in-memory `_cache_questions` + `_categories_cache` immediately on Render.
     3. Trigger optional GitHub Repository Dispatch / Vercel Deploy Hook (`VERCEL_DEPLOY_HOOK_URL`) OR allow Vercel workers to detect `db_catalog_revision > bundle.db_catalog_revision` automatically!
5. **Mandatory Safe Fallback Behavior (Never Serve Corrupted or Broken State):**
   - Boot-time loader order in `AvtotestProductEngine`:
     1. Check local/packaged `canonical_bundle.json` -> verify `schema_version == 2` and `sha256(questions) == payload_sha256`.
     2. Check `system_settings.catalog_version` on Turso (if Turso enabled).
     3. **Case A (Match):** Load bundle directly in `<80ms` RAM parse (`0` heavy Turso catalog transfer!).
     4. **Case B (Bundle Missing, Corrupted SHA-256, or `db_catalog_revision` Stale):** Log structured warning (`CATALOG_BUNDLE_STALE_FALLBACK`), **bypass bundle cleanly**, execute live Turso SQL catalog preload (`canonical_questions` + `canonical_translations` + `canonical_answers`), populate in-memory cache + TTL refresh, and emit admin metric alert so bundle rebuild/deploy runs asynchronously.
     5. Never fail closed if the JSON bundle is absent/stale while Turso is healthy; conversely, if Turso is temporarily unreachable on cold start and SHA-256-valid bundle exists, serve read-only catalog from verified bundle while flagging degraded mode!
6. **Cache Headers (`vercel.json` & API):**
   - Content-hashed URL or `ETag` based on `bundle_version` for browser/Mini App static caching (`Cache-Control: public, max-age=300, stale-while-revalidate=3600` for `/api/categories` rather than stale `1h` unversioned caching, or cache-busted `?v=<catalog_version>`).

---

## PART VII — LEGAL & EDUCATIONAL CONTENT VERIFICATION GOVERNANCE

> **Zero-Hallucination Rule (`[PROPOSED DECISION]`):** AI-generated explanations or legal citations (`GeminiService` or offline enrichment scripts) **MUST NEVER** be auto-marked as `VERIFIED`, overwritten onto canonical truths silently, or displayed as official Uzbekistan law without primary-source provenance and human sign-off.

### 7.1 Current Content Quality Baseline (`[VERIFIED FACT]`)
Read-only SQL forensics show exact gaps across `1,327` canonical questions (`3,981` translations):
- **Missing `legal_reference` (`canonical_questions`):** **`32` / `1,327` (`2.41%`)** — **100% of them are `CQ-1296..CQ-1327`** (left `NULL` by `StagingManager.approve_question()`). Meanwhile `1,295 / 1,295` `CANON-YHQ-*` questions have non-null `legal_reference`, though only `1,046` have `LEGAL_REFERENCE_FOUND` and `4` have `LEGAL_CONTENT_MATCHED` (`228` `CANON-*` are `SOURCE_CONFIRMED` and `17` `MULTI_SOURCE_CONFIRMED` — meaning their `legal_reference` came from scraped source strings or chapter heuristics rather than confirmed `lex.uz` content match!).
- **Missing `explanation` (`canonical_translations`):**
  - `uz_latn`: **`107` / `1,327`** missing (`100` in `CANON-*` + `7` in `CQ-*`)
  - `uz_cyrl`: **`112` / `1,327`** missing (`105` in `CANON-*` + `7` in `CQ-*`)
  - `ru`: **`114` / `1,327`** missing (`107` in `CANON-*` + `7` in `CQ-*`)
- **Critical Provenance Risk (`[VERIFIED FACT]`):** `StagingManager` sets `legal_act_title = 'Cabinet of Ministers Resolution No. 172'` automatically on approval even when `legal_reference IS NULL` and even before checking whether a question concerns first-aid/mechanical topics outside Resolution No. 172!

### 7.2 Mandatory Provenance Schema & Verification Workflow

Add strict provenance governance columns (Phase 1E schema / metadata extension):
- `legal_doc_title` (e.g., `"Vazirlar Mahkamasining 172-son qarori (YHQ)"` vs `"Birinchi tibbiy yordam qo'llanmasi"` vs `NULL`)
- `legal_doc_url` (canonical URL, e.g. `https://lex.uz/docs/5963102`)
- `legal_chapter` / `legal_clause` (exact chapter/band/ilova, e.g. `"13-bob, 99-band"`, NOT vague placeholders)
- `legal_effective_date` / `legal_act_version` (e.g. `"2022-05-01"`)
- `legal_verification_status` Enum:
  - `VERIFIED_PRIMARY_LAW` — Verified directly against primary Uzbekistan legal text (`lex.uz/docs/5963102` or updated VMQ amendments) + human reviewer.
  - `VERIFIED_FIRST_AID_OR_TECH` — Validated medical first-aid / technical maintenance rule outside YHQ articles `1–29` (explicitly cites technical/medical standard instead of faking a VMQ 172 clause).
  - `SOURCE_HINT_UNVERIFIED` — Copied from `yesprava`/`propdd` scraper teaser; needs primary-text cross-check.
  - `AI_DRAFT_PENDING_REVIEW` — AI-proposed draft explanation/citation; **blocked from showing as verified** to end users (shown only in Admin Editorial Queue).
  - `UNRESOLVED_LEGAL_REVIEW` — Explicitly unresolved after audit; UI displays neutral pedagogical answer explanation (`official answer confirmation`) without fabricated article badges, and queues item for domain expert review.
- `reviewed_by`, `reviewed_at`

### 7.3 Answering the "100% Legal-Reference Coverage" Realism Question (`[UNRESOLVED ITEM U-02]`)
- **`[PROPOSED DECISION]`**: Forcing `"100% of 1,327 questions must carry a VMQ 172 clause"` is **unrealistic and dangerous** because:
  1. Some official driving exam questions cover **first aid** (e.g., `yod nastoykasi` / bleeding / fractures), **defensive driving physics** (braking distance / centrifugal force), or **general mechanical checks** that do not map to a numbered YHQ traffic paragraph.
  2. Forcing `100%` encourages fabricating imprecise chapter links.
- **Recommended Realistic Standard:**
  - **`100% Classification Completeness`:** Every single one of `1,327` questions has an accurate non-empty `legal_verification_status` (`0` silent `NULL`s).
  - **`100% Grounded Primary-Law Citation` on legal-rule questions**, PLUS **`VERIFIED_FIRST_AID_OR_TECH`** on non-statutory medical/technical questions, PLUS transparent **`UNRESOLVED_LEGAL_REVIEW`** quarantine for any ambiguous item until verified against primary law by a human reviewer.
  - **Strict 3-Language Parity Rule (`uz_latn`, `uz_cyrl`, `ru`):** Every explanation edit/addition must update all 3 scripts simultaneously and preserve identical canonical answer letter (`A/B/C/D`), numeric speed/distance limits, and clause numbers. Machine transliteration or LLM translation must enter as `AI_DRAFT_PENDING_REVIEW` and pass a bilingual parity diff check (numbers + negated terms + clause tokens match across all 3 scripts).

---

## PART VIII — ARCHITECTURAL INCONSISTENCIES RESOLVED

### 8.1 Phase Boundaries: SM-2 Spaced Repetition Strictly Moved Out of Phase 1 (`[PROPOSED DECISION]`)
- **Resolution:** Zero SM-2 tables (`user_question_srs`, `ease_factor`, `interval_days`, `next_review_at`) or adaptive scheduling algorithms will touch Phase 1.
  - **Phase 1:** Read-only forensics -> Backup & restore drill -> Safe archive prototype (`0` broken sync/tests) -> SQLite/Turso parity (`user_ticket_progress`, `execute_batch()`, `PRAGMA foreign_keys`) -> Legal/explanation governance -> Production migration readiness.
  - **Phase 5 (`SRS & Mastery Engine`):** Design and deploy SM-2 memory scheduling schema cleanly on top of the stabilized Turso/SQLite foundation, preserving backward compatibility with `user_mistakes` and `user_ticket_progress`.

### 8.2 SQLite vs Turso SQL Dialect, `PRAGMA` & Transaction Atomicity Matrix (`[VERIFIED FACT]` + `[PROPOSED DECISION]`)

| Behavior | Local SQLite (`sqlite3`) | Production Turso (`TursoConnection` / `libsql-client`) | Blueprint Resolution (`[PROPOSED DECISION]`) |
| :--- | :--- | :--- | :--- |
| **`PRAGMA foreign_keys = ON`** | Applied in `get_db_connection()` (`src/db_adapter.py:272`), NOT in raw `sqlite3.connect()` calls | **NOT sent** inside `TursoConnection`! Needs `PRAGMA foreign_keys = ON` per transaction/batch | Enforce a single DB factory across `src/` (no raw `sqlite3.connect` in app/sync modules); prepend `PRAGMA foreign_keys = ON` on every mutating batch/session or enforce FK checks explicitly in migration CI. |
| **Multi-statement Transactions** | Interactive `BEGIN ... COMMIT / ROLLBACK` via `conn.commit()` | **`commit()` & `rollback()` are NO-OPs (`pass`)!** Each `cur.execute()` autocommits over HTTP | Refactor multi-table writes (`StagingManager.approve_question`, `IncrementalUnifier`, payment order settlements) to use `execute_batch(conn, stmts)` which maps to atomic `_client.batch()`. Verify HTTP 200 all-or-nothing rollback in Sub-Gate `1D`. |
| **`executescript()`** | Native C SQLite script execution | Splits blindly on `";"` (`src/db_adapter.py:218`) — breaks strings containing semicolons! | Ban `executescript()` on Turso migrations; execute parsed statement lists via `execute_batch()` or dedicated migration runner. |
| **Migrations Entrypoint** | `run_migrations()` runs locally | **`run_migrations()` explicitly returns early if `is_turso_enabled()`!** (`src/database_migrations.py:313`) | Replace ad-hoc `_ensure_ticket_progress_table()` lazy DDL catches with a formal versioned `schema_migrations` table + explicit CLI runner (`scripts/migrate_db.py --target local|staging-turso|prod-turso`) executed in gated deploys. |
| **`PRAGMA integrity_check` / `.backup()`** | Native file operations | Not applicable identically over Hrana HTTP | Local integrity verified via `PRAGMA integrity_check`; Turso verified via logical `SELECT` checksum parity + FK orphan anti-join queries (`LEFT JOIN ... WHERE parent IS NULL`). |

### 8.3 Async Database Concurrency & `_thread_local` Thread Safety (`[VERIFIED FACT]` + `[PROPOSED DECISION]`)
- **Current Bug Risk (`[VERIFIED FACT]`):** `src/db_adapter.py:13` stores a synchronous `libsql_client` on `threading.local()` (`_thread_local.turso_client`). Meanwhile FastAPI mixes synchronous `def` routes (`src/api/routes_theory.py:111`, executed on AnyIO worker threads) and `async def` routes (`src/api/routes_ai.py:59`, `src/admin/routes_admin_questions.py:33`, running directly on the main asyncio event loop and calling synchronous `get_db_connection()`!).
  - Calling synchronous HTTP `TursoConnection` inside an `async def` FastAPI handler **blocks the entire ASGI event loop** (stalling Telegram Bot polling, MTProto, and concurrent HTTP requests during slow Turso calls!).
  - Sharing `_thread_local` across `asyncio.to_thread` vs event loop threads is safe *only* if every single blocking DB operation executes inside bounded worker threads (either sync `def` endpoints or `await asyncio.to_thread(...)`), AND no `TursoConnection` object is ever created in one thread and mutated/closed in another!
- **Target Resolution (`[PROPOSED DECISION]`):**
  1. Never call blocking `TursoConnection` queries directly inside `async def` functions on the event loop; wrap DB service calls in `await asyncio.to_thread(...)` (or switch high-concurrency routes to sync `def` + dedicated bounded executor/async `libsql_client` evaluation in Phase 2/7).
  2. Enforce thread-ownership assertions in DB helper: connection/client lookup always stays thread-local inside the synchronous DAO unit of work and returns plain Python `dict`/`dataclass` DTOs across thread boundaries.

### 8.4 Render Worker Separation vs `render.yaml` `plan: free` Budget Reality (`[VERIFIED FACT]` + `[UNRESOLVED ITEM U-03]`)
- **Current Reality (`[VERIFIED FACT]`):** `render.yaml:1-33` defines **1 single Web Service** (`rully-all-in-one`, `plan: free`, `singapore`, `512 MB` RAM estimate, shared CPU, sleeps after `15m` inactivity unless self-pinged). That single process hosts: Uvicorn FastAPI + Order Expiration (`15m`) + Periodic Question Sync (`12h` BeautifulSoup web scraping!) + Telethon MTProto daemon + Aiogram Bot polling + Keepalive Pinger (`7m`).
- **Inconsistency Resolved:** Splitting FastAPI, MTProto/Bot, and Scraper into separate **Render Background Worker** services is architecturally cleaner **ONLY IF paid Render plans ($7+/mo per service) are authorized** — `plan: free` on Render does not run perpetual paid background worker services alongside a web service without upgrade costs or PaaS migration.
- **Two Concrete Paths (Decision `U-03` Required):**
  - **Option A ($0/mo Free-Tier Compatible Isolation):** Keep 1 Render service for FastAPI + Bot polling + MTProto daemon (with hardened supervised task wrappers, structured backoff, memory monitoring, and circuit breakers), AND **offload heavy periodic scraping (`12h` `YesPrava`/`ProPDD` checks) to a scheduled GitHub Actions workflow** calling an authenticated staging webhook — removing HTML parsing spikes from Render RAM completely!
  - **Option B (Paid Upgrade `$7–$21+/mo`):** Split Web API (Render/Vercel), Dedicated MTProto+Bot Worker (Render Background Worker), and Scheduled Cron Jobs cleanly across separate OS processes/containers.

### 8.5 Vercel Serverless Cold Start vs Catalog Load Separation (`[VERIFIED FACT]` + `[PROPOSED DECISION]`)
- **Correction to Blueprint v1:** Deserializing a verified ~`5.6 MB` `canonical_bundle.json` (or pruned API-only bundle ~`2.8 MB` excluding raw admin metadata) into RAM takes roughly **`< 80ms`** in Python, **NOT** the entire Vercel cold start!
- **True Vercel Cold-Start Budget Breakdown:**
  1. Python runtime container init + ASGI import chain (`FastAPI`, `Pydantic`, `cryptography`, `argon2`, `libsql_client`, router tree — `api/index.py` loads `src.api.main` including ALL admin routers even on public Mini App requests!): typically **`600ms–1,800ms+` `[ASSUMPTION — benchmark in Phase 7]`**.
  2. Turso cold HTTPS TLS handshake + user auth query (`get_current_user` misses `_user_cache` on fresh container): **`150ms–450ms` `[ASSUMPTION — region `bom1` Vercel <-> `aws-ap-south-1` Turso Mumbai co-location reduces RTT]`**.
  3. **Optimization Lever (`Phase 2/7`):** Lazy-split `/api/admin/*` routers out of the critical Mini App cold-start path (or mount on dedicated lightweight ASGI entrypoints) so user Mini App Lambdas don't import heavy admin dependencies (`argon2`, `telethon`, `bs4`, `sync` modules).

---

## PART IX — RELEASE, TEST GOVERNANCE & RISK-TO-TEST TRACEABILITY MATRIX

### 9.1 Strict QA & Release Rules (`[PROPOSED DECISION]`)
1. **Realistic, Measurable Performance & Reliability Targets (replacing absolutes):**
   - **Vercel Warm API P95 Latency (`/api/categories`, `/api/tickets`, `/api/session/start`):** `< 250ms` (`bom1` -> `aws-ap-south-1`).
   - **Cold-Start Catalog Deserialization Overhead:** `< 80ms` (with verified bundle); total cold-start P95 measured and tracked against `< 2,500ms` budget rather than impossible `"0ms"` claims.
   - **Zero Unhandled `5xx` Rate:** `0%` unhandled `5xx` during Playwright + API integration suite & synthetic spike load tests (`>= 20` req/s).
   - **New Business Logic Coverage:** `>= 90%` unit/integration coverage on SM-2, payment reconciliation, staging atomic batching, and auth security paths.
2. **Zero Silent Test Weakening / Deletion Policy:**
   - Agents/developers are **STRICTLY FORBIDDEN** from deleting, relaxing assertions on, or silently marking `@pytest.mark.skip` on failing existing tests (`tests/test_master_database.py`, `tests/test_unified_product.py`, `tests/test_question_sync.py`, `tests/test_phase1_security.py`, `tests/test_phase2_concurrency.py`, `tests/test_rully_2_architecture.py`, etc.).
   - Any test legitimately retired or retargeted due to an approved DB archive migration MUST link to the approved Gate decision, explain why, re-verify equivalent assertions against `rully_etl_archive.sqlite`, and include a sunset/migration note.
   - Any temporary skipped test MUST declare `@pytest.mark.skip(reason="[TICKET/GATE] exact reason + owner + sunset date")`.
3. **Expected Auth Gates vs Errors (`HTTP Semantics`):**
   - Unauthenticated probes to `/api/admin/auth/me` returning **`HTTP 401 Unauthorized`** (or unauthenticated Mini App endpoints in production mode returning **`401`**) are **EXPECTED SECURITY PASSES**, never application errors!
   - Automated Playwright / curl smoke monitors MUST explicitly assert expected status codes (`401` when logged out, `200` with valid session cookie/HMAC header) and only fail on unexpected status codes (`500–599`, unexpected `404`/`403`, or uncaught JS console/network errors excluding intentional auth checks).
4. **Mandatory Staging Verification & Tested Rollback Drills:**
   - Every schema migration or release candidate deploys first to **staging Turso + preview Vercel/staging Render** -> executes full automated regression + Playwright responsive E2E (`375×812` Telegram WebView & `1440×900` Admin) -> executes & verifies **rollback drill** before production promotion.

### 9.2 Risk-to-Test Traceability Matrix

| Risk ID | Architectural / Data Risk | Mitigating Control | Verification Test / Evidence Required |
| :--- | :--- | :--- | :--- |
| **`R-01`** | Loss of live Turso user/payment/AI data (`telegram_users`, `payment_orders`, `ai_conversations`) during DB work | Sub-Gate `1B` WAL-safe backup + Turso logical dump + SHA-256 + Sub-Gate `1F` separate sign-off + immutable prod-first updates | Actual restore drill onto temp SQLite + staging Turso count parity script (`exit 0`, zero diff). |
| **`R-02`** | Archive separation crashes `DiffDetector`, `StagingManager`, `Exporter`, or breaks `test_master_database.py` | Phased Tier 0 (`0`-ref snapshot tables) before Tier 1 refactor (`canonical_source_links`, decoupled `StagingManager`) | `pytest tests/test_question_sync.py tests/test_unified_product.py` + retargeted archive verification pass without skipped tests. |
| **`R-03`** | Non-atomic multi-step writes on Turso (`TursoConnection.rollback()` is no-op) corrupt staged question approval or payments | Replace sequential `cur.execute()` with atomic `execute_batch()` (`_client.batch()`) + Turso FK enforcement checks | Fault-injection test forcing failure on step 5 of `approve_question` -> assert 0 partial rows committed. |
| **`R-04`** | Missing `user_ticket_progress` table on Turso triggers runtime SQL error in analytics/ticket API | Formal schema migration runner (`Sub-Gate 1D`) syncing all `43+` tables & indexes to staging then prod Turso | `sqlite_master` parity test comparing local SQLite vs Turso staging (`diff == empty`), `/api/tickets` & `/api/user/analytics` E2E test. |
| **`R-05`** | `canonical_bundle.json` absent, corrupted, or stale after admin edit serves outdated answers | SHA-256 verification + `system_settings.catalog_version` handshake + automatic Turso SQL fallback | Unit tests simulating missing bundle, tampered byte SHA-256, and mismatched `catalog_version` -> verify automatic Turso fallback & cache eviction. |
| **`R-06`** | AI assistant or batch script injects hallucinated VMQ 172 article or breaks 3-language parity | Strict `legal_verification_status` workflow + human approval queue + `AI_DRAFT_PENDING_REVIEW` quarantine | Bilingual/trilingual validator verifying option key + numeric/clause token consistency; assert zero unreviewed AI drafts in live API payload. |
| **`R-07`** | Blocking sync `TursoConnection` calls stall `async def` FastAPI routes / MTProto / Bot event loop | Wrap DB calls safely in `asyncio.to_thread` / worker threads; maintain strict thread ownership of `_thread_local` client | Concurrent load test (`locust`/`asyncio` 25 concurrent clients across `/api/ai/status`, `/api/tickets`, `/api/session/start`) with `0` deadlocks/timeouts. |
| **`R-08`** | Free Render `512 MB` RAM OOM or CPU freeze during 12h HTML scrape kills MTProto payment listener | Isolate/circuit-break internal scraper OR offload 12h scrape to GitHub Actions (Decision `U-03`) | Memory watermark profiling (`< 350 MB` peak RSS) + synthetic scraper exception test verifying MTProto stays `CONNECTED`. |

---

## PART X — ARCHITECTURAL OVERVIEW OF PHASES 2–8 (PRESERVED VISION + UPDATED DEPENDENCIES)

> **Scope Note:** Phases `2–8` carry forward the complete RULLY 2.0 product vision benchmarked against `bilet.run` and local frontend/backend audits, now cleanly aligned to the hardened Phase 1 database governance. Exact implementation specs for each subsequent phase will undergo deep sub-planning prior to their respective Gate approvals.

- **Phase 2 — Backend Sync, `canonical_bundle.json` & Admin Operations Hardening (Gate B):**
  - Implement atomic `execute_batch()` across `StagingManager`, `IncrementalUnifier`, and `OrderManager`; implement `canonical_bundle.json` SHA-256 versioning + `catalog_version` invalidation + Turso fallback; fix admin moderation UX so admins can enter `legal_chapter`, `legal_clause`, `legal_verification_status`, and 3-language explanations directly inside `/admin`.
- **Phase 3 — RULLY 2.0 Design System, Cockpit Visual Language & Core Navigation (Gate C):**
  - Replace generic flat card UI (`static/css/rully.css`, `static/index.html`) with a cohesive high-contrast **Driver's Cockpit** design system (daylight crisp clarity + OLED night mode, 48dp+ tactile touch targets for Telegram WebView thumb reach, speedometer readiness gauge building on generated exploratory dial concepts `speedometer_dial_base_clean_1795212196647.jpg` / `dual_cluster_cockpit_dashboard_1795212261639.jpg`, and clean 5-section navigation hierarchy inspired by `bilet.run`'s clarity).
- **Phase 4 — Quiz Engine UX, Road Signs Explorer, Shpargalka & Law Reader (Gate D):**
  - Structured study hub inspired by verified `bilet.run` UX strengths (`/` stats clarity, `/signs` visual categorized sign explorer, `/info/qoidalar` interactive rules chapters + penalty points calculator + condensed `Shpargalka` quick reference) integrated with RULLY's native `67` Bilet Grid, Topic Mastery, Mistake Bank, and instant verified legal-reference drawers (`UNRESOLVED_LEGAL_REVIEW` safely badged where still under review).
- **Phase 5 — Adaptive SM-2 Spaced Repetition & Personalized Readiness Engine (Gate E):**
  - **Moved cleanly out of Phase 1 into Phase 5.** Introduce `user_question_srs` (`ease_factor`, `interval_days`, `repetitions`, `lapses`, `next_review_at`) migrated identically to SQLite + Turso, feeding a daily `"Aqlli Takrorlash"` queue integrated with existing `user_mistakes`, `user_ticket_progress`, and Bayesian driver readiness scoring (`compute_driver_accuracy`).
- **Phase 6 — Telegram Bot UX Parity, Payment/MTProto Resilience & AI Ustoz Context Guardrails (Gate F):**
  - Deep-link Mini App cards + rich inline quizzes in `aiogram`, strict `UNMATCHED` Humo payment auto-reconciliation observability & admin alerts, and grounding `GeminiService` prompts in verified canonical facts + `canonical_questions.legal_reference` (forbidding fabricated law citations).
- **Phase 7 — Performance, Security Hardening & Full-Stack Observability (Gate G):**
  - Split public Mini App ASGI imports from heavy Admin/Telethon/Sync routers on Vercel (`api/index.py`) to cut cold starts; thread-safe async DB wrappers (`asyncio.to_thread`); strict CSP/CORS/rate-limit verification; Admin Audit & Structured Metrics Dashboard.
- **Phase 8 — Staging End-to-End Sign-Off, Rollback Drill & Controlled Production Rollout (Gate H):**
  - Zero-downtime staged rollout across Turso, Render, and Vercel, responsive Playwright audit (`375×812` & `1440×900`), smoke verification respecting semantic `401` checks vs true errors, and documented rollback readiness.

---

## PART XI — EXPLICIT UNRESOLVED DECISIONS REQUIRING USER APPROVAL

Before approving Gate A and entering **Sub-Gate 1A/1B**, the user must decide the following open items (`[UNRESOLVED ITEM]`):

1. **`[U-01]` Tier 1 ETL Archive Refactoring & Test Relocation Scope (`Phase 1C`):**
   - **Choice A (Recommended):** Perform Tier 0 (`archived_duplicate_source_traces`, `proposed_source_trace_cleanup`) + **full Tier 1 split**: move legacy `questions` (`5,977`), `answers` (`19,579`), `verification_records` (`5,945`), and heavy `raw_payload` blobs in `question_sources` (`7,415`) into `data/archive/rully_etl_archive.sqlite`; migrate `DiffDetector` & `StagingManager` onto `canonical_questions` + slim `canonical_source_links`; point `tests/test_master_database.py` at `data/archive/rully_etl_archive.sqlite` (preserving every assertion!).
   - **Choice B (Minimal Change):** Archive ONLY `archived_duplicate_source_traces` (`306`) & `proposed_source_trace_cleanup` (`306`), plus optional offline archival of `verification_records` (`5,945`), keeping `questions`/`answers`/`question_sources` untouched in runtime DB so sync & `tests/test_master_database.py` need zero refactoring (`~11 MB` remains in runtime DB).
2. **`[U-02]` Realistic Legal-Reference Classification Policy (`Phase 1E`):**
   - **Choice A (Recommended):** Replace `"100% VMQ 172 legal reference"` with **`100% Classified Provenance`**: `VERIFIED_PRIMARY_LAW` (VMQ 172 clause verified against `lex.uz/docs/5963102`), `VERIFIED_FIRST_AID_OR_TECH` (medical/mechanical non-statutory rule), and `UNRESOLVED_LEGAL_REVIEW` (transparently hidden/flagged instead of AI-guessed).
   - **Choice B:** Attempt strict VMQ 172 mapping for every possible traffic-rule item and leave non-VMQ questions unreferenced/quarantined until manual legal review completes.
3. **`[U-03]` Render Runtime Topology & Hosting Budget (`Phase 2 / Phase 6`):**
   - **Choice A ($0/mo Free-Tier Compatible, Recommended unless upgrading):** Keep 1 Render Web Service (`plan: free`) for API + Bot polling + MTProto listener with hardened supervised circuit breakers, and move periodic `12h` external source scraping to a **GitHub Actions Scheduled Workflow** calling a signed dry-run/staging endpoint (zero Render RAM spikes).
   - **Choice B (Paid Upgrade `$7–$21+/mo`):** Authorize adding dedicated Render Background Worker service(s) to physically isolate MTProto/Bot and Sync workers from the HTTP web server.
4. **`[U-04]` Source of Truth for Live Explanations / Curriculum Edits:**
   - Confirm whether **228 `CANON-*` items marked `SOURCE_CONFIRMED`** (not `LEGAL_REFERENCE_FOUND`) and the **32 `CQ-1296..CQ-1327` items** have an authoritative external textbook/official doc the admin team will supply in Sub-Gate `1E`, or whether we build an **Admin Editorial Verification Queue** inside `/admin` first so RULLY admins approve every draft (`AI_DRAFT_PENDING_REVIEW`) cleanly.
5. **`[U-05]` Vercel Cold-Start Route Split vs Single Deployment:**
   - Confirm whether `/api/admin/*` stays in `api/index.py` (using lazy FastAPI router/module loading on public routes) or splits cleanly onto Render Admin-only while Vercel serves public Mini App traffic (`/api/auth/*`, `/api/categories`, `/api/tickets`, `/api/session/*`, `/api/ai/*`, `/api/payments/*`) with smaller Lambda footprint.
6. **`[U-06]` Missing `user_ticket_progress` Table Remediation Timing:**
   - Authorize fixing the missing `user_ticket_progress` table on **Production Turso** during **Sub-Gate `1D`/`1F`** (explicit migration window) vs allowing `_ensure_ticket_progress_table()` lazy DDL to remain until Phase 1 finishes. *(Recommended: fix properly in Sub-Gate `1D` staging -> `1F` controlled Turso migration).*
7. **`[U-07]` Local `master_database.sqlite` Role Going Forward:**
   - Confirm treating Production Turso as the sole source of truth for user/financial/audit state and refreshing local dev snapshots via read-only sanitized exports (scrubbing PII/admin hashes/session strings for developer testing), never syncing local `telegram_users` or `audit_merge_log` upward to Turso.

---

**END OF REVISED PHASE 0 BLUEPRINT — AWAITING GATE A REVIEW & DECISIONS `U-01`–`U-07` BEFORE ANY CODE OR DATABASE ACTION**
