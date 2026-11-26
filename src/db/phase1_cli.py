"""
Phase 1 Controlled Execution CLI (Phases 1C -> 1D -> 1E -> 1F).

Supports:
  --stage-verify      Decrypts Phase 1B Turso backup into an isolated ephemeral SQLite DB
                      and proves Tier 0 archival + Migrations 001/002 + Provenance seeding
                      + full rollback without touching local master DB or Production Turso.
  --apply-production  Takes a fresh pre-1F encrypted snapshot of Production Turso & local DB,
                      executes Phase 1C (Tier 0 only), Phase 1D, Phase 1E cleanly on Production
                      Turso with post-migration verification, then refreshes local SQLite via
                      U-07 sanitized downward export.
"""

import argparse
from datetime import datetime
import json
import os
import sqlite3
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from dotenv import load_dotenv
from src.db.archive_tier0 import (
    TIER0_TABLES,
    extract_tier0_from_connection,
    rollback_tier0_from_archive,
)
from src.db.migrations_v2 import (
    apply_phase1_migrations,
    rollback_phase1_migrations_local_test,
    verify_schema_parity,
)
from src.db.provenance_classifier import audit_and_seed_provenance
from src.db.sanitized_export import export_sanitized_dev_sqlite
from src.db.sqlite_utils import (
    backup_sqlite_wal_safe,
    compute_file_sha256,
    compute_rows_sha256,
    list_user_tables,
)
from src.db_adapter import close_shared_turso_client, get_db_connection, is_turso_enabled


def _load_phase1b_helpers():
    """Imports DPAPI/AES decrypt & SQL split helpers cleanly without side effects."""
    import scratch.phase1b_backup_and_restore as p1b
    return p1b


def run_staging_verification(vault_dir: str) -> dict:
    """Replays full Phase 1 against an isolated SQLite replica decrypted from Phase 1B backup."""
    p1b = _load_phase1b_helpers()
    files = os.listdir(vault_dir)
    key_file = next(f for f in files if f.endswith(".key.dpapi"))
    sql_file = next(f for f in files if f.endswith(".sql.enc"))

    with open(os.path.join(vault_dir, key_file), "rb") as f:
        dek = p1b.dpapi_unprotect(f.read())
    with open(os.path.join(vault_dir, sql_file), "rb") as f:
        sql_text = p1b.aesgcm_decrypt(dek, f.read(), sql_file.encode("utf-8")).decode("utf-8")
    del dek

    stmts = p1b.split_sqlite_statements(sql_text)
    del sql_text

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    stage_db = os.path.join(ROOT, "scratch", f"_phase1f_staging_sim_{ts}.sqlite")
    stage_archive = os.path.join(ROOT, "scratch", f"_phase1f_staging_arch_{ts}.sqlite")
    for p in (stage_db, stage_archive):
        if os.path.exists(p):
            os.remove(p)

    conn = sqlite3.connect(stage_db)
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        for st in stmts:
            conn.execute(st)
        conn.commit()

        before_counts = {}
        for t in list_user_tables(conn):
            before_counts[t] = conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]

        # 1. Test Tier 0 archive + rollback + re-apply
        t0_res = extract_tier0_from_connection(
            conn, stage_archive, drop_from_runtime=True, source_label="staging_turso_sim"
        )
        t0_rb = rollback_tier0_from_archive(conn, stage_archive)
        t0_re = extract_tier0_from_connection(
            conn, stage_archive, drop_from_runtime=True, source_label="staging_turso_sim"
        )

        # 2. Test Migrations 001 + 002 + Provenance audit
        mig_res = apply_phase1_migrations(conn)
        prov_res = audit_and_seed_provenance(conn, admin_actor="phase1f_staging_sim")
        parity_final = verify_schema_parity(conn)

        # Confirm zero data loss on protected tables
        protected_preserved = {}
        for t, bcnt in before_counts.items():
            if t in TIER0_TABLES:
                continue
            acnt = conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
            assert acnt == bcnt, f"Data loss/mismatch on {t}: before={bcnt}, after={acnt}"
            protected_preserved[t] = acnt

        # 3. Verify clean migration rollback drill on staging DB copy too
        rb_mig = rollback_phase1_migrations_local_test(conn)
        assert conn.execute("SELECT COUNT(*) FROM session_answers").fetchone()[0] == before_counts["session_answers"]

        # Re-apply cleanly and check final PRAGMAs
        mig_final = apply_phase1_migrations(conn)
        prov_final = audit_and_seed_provenance(conn, admin_actor="phase1f_staging_sim")
        int_chk = conn.execute("PRAGMA integrity_check;").fetchall()
        fk_chk = conn.execute("PRAGMA foreign_key_check;").fetchall()
        assert int_chk == [("ok",)]
        assert fk_chk == []

        return {
            "status": "STAGING_SIMULATION_PASSED",
            "tier0_extract_and_rollback": {
                "initial": t0_res,
                "rollback": t0_rb,
                "reapply": t0_re,
            },
            "migration_parity": parity_final,
            "migration_rollback_tested": rb_mig["rolled_back"],
            "provenance_audit": prov_final,
            "protected_tables_verified_count": len(protected_preserved),
            "integrity_check": int_chk,
            "foreign_key_check": fk_chk,
        }
    finally:
        conn.close()
        for p in (stage_db, stage_archive):
            if os.path.exists(p):
                os.remove(p)


def run_production_phase1f() -> dict:
    """
    Controlled Phase 1F Production Execution:
      1. Fresh Pre-1F Encrypted Backup of Turso & Local SQLite into ~/.rully_vault
      2. Execute Tier 0 archive (U-01) -> data/archive/rully_tier0_archive.sqlite
      3. Execute Phase 1D/1E Migrations + Deterministic Provenance Seeding on Turso
      4. Verify zero user/payment/exam/AI/catalog data loss + schema parity on Turso
      5. Refresh local master_database.sqlite via U-07 Sanitized Downward Export
    """
    load_dotenv(os.path.join(ROOT, ".env"))
    assert is_turso_enabled(), "TURSO_DATABASE_URL / TURSO_AUTH_TOKEN must be configured for Phase 1F."

    p1b = _load_phase1b_helpers()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    vault_root = p1b.VAULT_ROOT
    p1b.restrict_directory_acl(vault_root)
    pre_1f_dir = p1b.create_non_overwriting_dir(vault_root, f"pre_1f_{ts}")

    local_db = os.path.join(ROOT, "master_database.sqlite")
    local_pre_1f = os.path.join(pre_1f_dir, f"local_pre_1f_{ts}.sqlite")
    backup_sqlite_wal_safe(local_db, local_pre_1f, allow_overwrite=False)

    # Take fresh read-only encrypted Turso snapshot right before 1F mutations
    turso_conn = get_db_connection()
    guard = p1b.ReadOnlyTursoGuard(turso_conn._client)
    try:
        rs_m = guard.execute_select("SELECT type, name, tbl_name, sql FROM sqlite_master ORDER BY type, name")
        tables_ddl = {r[1]: r[3] for r in rs_m.rows if r[0] == "table" and not r[1].startswith("sqlite_")}
        indexes_ddl = [{"name": r[1], "tbl_name": r[2], "sql": r[3]} for r in rs_m.rows if r[0] == "index" and not r[1].startswith("sqlite_") and r[3]]
        turso_tables = sorted(tables_ddl.keys())

        pre_counts = {}
        stmts = [f"SELECT '{t}', COUNT(*) FROM \"{t}\"" for t in turso_tables]
        for i in range(0, len(stmts), 20):
            for rset in guard.batch_select(stmts[i:i + 20]):
                pre_counts[rset.rows[0][0]] = rset.rows[0][1]

        rs_seq = guard.execute_select("SELECT name, seq FROM sqlite_sequence ORDER BY name")
        pre_seq = {r[0]: r[1] for r in rs_seq.rows}

        # Read full rows cleanly
        turso_data = {}
        digests = {}
        for t in turso_tables:
            rows_all = []
            cols = None
            last_rowid = None
            while True:
                if last_rowid is None:
                    rsp = guard.execute_select(f'SELECT rowid AS _r_rowid, * FROM "{t}" ORDER BY rowid LIMIT 500')
                else:
                    rsp = guard.execute_select(
                        f'SELECT rowid AS _r_rowid, * FROM "{t}" WHERE rowid > ? ORDER BY rowid LIMIT 500',
                        [last_rowid],
                    )
                if cols is None:
                    cols = list(rsp.columns[1:])
                if not rsp.rows:
                    break
                for r in rsp.rows:
                    last_rowid = r[0]
                    rows_all.append(tuple(r[1:]))
                if len(rsp.rows) < 500:
                    break
            assert len(rows_all) == pre_counts[t]
            digests[t] = compute_rows_sha256(rows_all)
            turso_data[t] = {"columns": cols or [], "rows": [[p1b.encode_json_cell(v) for v in r] for r in rows_all]}

        # Encrypt Pre-1F Turso snapshot at rest
        dek = os.urandom(32)
        dpapi_dek = p1b.dpapi_protect(dek)
        snap_json = json.dumps(
            {
                "timestamp": ts,
                "tables_ddl": tables_ddl,
                "indexes_ddl": indexes_ddl,
                "sqlite_sequence": pre_seq,
                "table_counts": pre_counts,
                "table_digests": digests,
                "table_data": turso_data,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")

        key_path = os.path.join(pre_1f_dir, f"turso_pre_1f_{ts}.key.dpapi")
        json_enc = os.path.join(pre_1f_dir, f"turso_pre_1f_{ts}.json.enc")
        with open(key_path, "wb") as f:
            f.write(dpapi_dek)
        with open(json_enc, "wb") as f:
            f.write(p1b.aesgcm_encrypt(dek, snap_json, os.path.basename(json_enc).encode("utf-8")))
        del dek, dpapi_dek, snap_json, turso_data

        with open(os.path.join(pre_1f_dir, "SHA256SUMS.txt"), "w", encoding="utf-8") as mf:
            for p in (local_pre_1f, key_path, json_enc):
                mf.write(f"{compute_file_sha256(p)}  {os.path.basename(p)}\n")

        # 2. Phase 1C (Tier 0 Only) -> Archive to data/archive/rully_tier0_archive.sqlite & vault copy
        archive_repo_path = os.path.join(ROOT, "data", "archive", "rully_tier0_archive.sqlite")
        archive_vault_copy = os.path.join(pre_1f_dir, f"tier0_archive_{ts}.sqlite")
        tier0_res = extract_tier0_from_connection(
            turso_conn, archive_repo_path, drop_from_runtime=True, source_label="production_turso"
        )
        if os.path.exists(archive_repo_path):
            backup_sqlite_wal_safe(archive_repo_path, archive_vault_copy, allow_overwrite=False)

        # 3. Phase 1D/1E Migrations on Production Turso
        mig_res = apply_phase1_migrations(turso_conn)
        assert mig_res["parity"]["passed"] is True, f"Turso schema parity failed: {mig_res}"

        # 4. Phase 1E Provenance Audit on Production Turso
        prov_res = audit_and_seed_provenance(turso_conn, admin_actor="phase1f_prod_rollout")

        # 5. Post-1F Production Parity Verification
        post_tables = list_user_tables(turso_conn)
        post_counts = {}
        c_stmts = [f"SELECT '{t}', COUNT(*) FROM \"{t}\"" for t in post_tables]
        for i in range(0, len(c_stmts), 20):
            for rset in turso_conn.batch(c_stmts[i:i + 20]):
                post_counts[rset.rows[0][0]] = rset.rows[0][1]

        preserved_diff = {}
        for t, cnt in pre_counts.items():
            if t in TIER0_TABLES:
                continue
            if post_counts.get(t) != cnt:
                preserved_diff[t] = {"before": cnt, "after": post_counts.get(t)}
        assert not preserved_diff, f"Protected Production Turso tables changed unexpectedly: {preserved_diff}"
        assert "archived_duplicate_source_traces" not in post_tables
        assert "proposed_source_trace_cleanup" not in post_tables

        # 6. Refresh local master_database.sqlite cleanly via Decision U-07 Sanitized Downward Export
        sanitized_res = export_sanitized_dev_sqlite(turso_conn, local_db)

        return {
            "status": "PHASE_1F_COMPLETE",
            "pre_1f_vault_dir": pre_1f_dir,
            "tier0_archive": tier0_res,
            "turso_migrations": mig_res,
            "turso_provenance_audit": prov_res,
            "turso_pre_counts": pre_counts,
            "turso_post_counts": post_counts,
            "protected_tables_100pct_preserved": True,
            "local_sanitized_refresh": sanitized_res,
        }
    finally:
        turso_conn.close()
        close_shared_turso_client()


def main():
    parser = argparse.ArgumentParser(description="RULLY Phase 1 Controlled Execution CLI")
    parser.add_argument("--stage-verify", action="store_true", help="Run staging drill against Phase 1B encrypted Turso replica")
    parser.add_argument("--apply-production", action="store_true", help="Apply Phase 1C/1D/1E/1F to Production Turso + refresh sanitized local dev DB")
    parser.add_argument("--refresh-local-sanitized", action="store_true", help="Read-only downward sanitized export from Turso to local master_database.sqlite (U-07)")
    parser.add_argument(
        "--vault-dir",
        default=os.path.join(os.path.expanduser("~"), ".rully_vault", "phase_1b_20261126_222549"),
        help="Phase 1B vault directory containing encrypted Turso backup",
    )
    args = parser.parse_args()

    if args.stage_verify:
        out = run_staging_verification(args.vault_dir)
        out_path = os.path.join(ROOT, "scratch", "phase1f_staging_results.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2, ensure_ascii=False)
        print(json.dumps(out, indent=2, ensure_ascii=False))
    elif args.refresh_local_sanitized:
        load_dotenv(os.path.join(ROOT, ".env"))
        assert is_turso_enabled(), "TURSO_DATABASE_URL / TURSO_AUTH_TOKEN required"
        tconn = get_db_connection()
        try:
            res = export_sanitized_dev_sqlite(tconn, os.path.join(ROOT, "master_database.sqlite"))
            print(json.dumps(res, indent=2, ensure_ascii=False))
        finally:
            tconn.close()
            close_shared_turso_client()
    elif args.apply_production:
        out = run_production_phase1f()
        out_path = os.path.join(ROOT, "scratch", "phase1f_production_results.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2, ensure_ascii=False)
        print(f"Wrote {out_path}")
        print(json.dumps({
            "status": out["status"],
            "pre_1f_vault_dir": out["pre_1f_vault_dir"],
            "turso_migrations_passed": out["turso_migrations"]["parity"]["passed"],
            "provenance_counts": out["turso_provenance_audit"]["classification_counts"],
            "protected_tables_100pct_preserved": out["protected_tables_100pct_preserved"],
            "local_sanitized_refresh_status": out["local_sanitized_refresh"]["status"],
        }, indent=2, ensure_ascii=False))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
