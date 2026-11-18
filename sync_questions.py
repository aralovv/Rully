#!/usr/bin/env python3
"""
RULLY Automated Driving Test Theory Question Synchronizer CLI.

Usage examples:
  python sync_questions.py --status
  python sync_questions.py --check
  python sync_questions.py --sync
  python sync_questions.py --source yesprava --check
  python sync_questions.py --source yesprava --sync
"""
import sys
import argparse
from datetime import datetime

# Windows encoding safety
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from src.sync.service import QuestionSyncService

def format_status(service: QuestionSyncService):
    print("=" * 65)
    print("🚦 RULLY — MANBALAR HOLATI VA SAVOLLAR BAZASI METRIKALARI")
    print("=" * 65)

    metrics = service.get_database_metrics()
    print(f"📊 Bazadagi Kanonik Savollar: {metrics['canonical_questions']} ta")
    print(f"🌐 3 tildagi tarjimalar:       {metrics['canonical_translations']} ta")
    print(f"🖼️ Saqlangan WebP rasmlar:     {metrics['total_images']} ta")
    print(f"📑 Jami qamrab olingan biletlar: {metrics['total_tickets']} ta")
    print("-" * 65)

    print("Qidirilayotgan Manbalar:")
    statuses = service.get_all_source_statuses()
    for s in statuses:
        status_ico = "🟢 ONLAYN" if s["is_online"] else "🔴 OFLAYN"
        print(f" • {s['source_name']} ({s['source_url']}):")
        print(f"     Holat: {status_ico} | Tezlik: {s['response_time_ms']} ms")
        print(f"     Mavjud biletlar: {s['tickets_count']} ta (~{s['estimated_questions']} savol)")
        if s.get("error"):
            print(f"     Xatolik: {s['error']}")
    print("=" * 65)

def run_check(service: QuestionSyncService, source: str = "all"):
    print(f"🔍 [{datetime.now().strftime('%H:%M:%S')}] Manbalar bo‘yicha yangilanishlar tekshirilmoqda ({source})...", flush=True)
    res = service.check_for_updates()

    print("\nTekshiruv Natijasi:")
    print("-" * 65)
    for rep in res["source_reports"]:
        if source != "all" and rep["source_code"] != source:
            continue
        changes_str = "⚠️ O‘ZGARISHLAR BOR!" if rep["has_changes"] else "✅ Yangilik yo‘q (Hammasi dolzarb)"
        print(f"[{rep['source_name']}] {changes_str}")
        print(f"  • Onlayn biletlar: {rep['total_tickets_online']} ta")
        print(f"  • Yangi biletlar:  {rep['new_tickets'] if rep['new_tickets'] else 'Mavjud emas'}")
        print(f"  • Yangi savollar:  {rep['new_questions_count']} ta")
        print(f"  • Tuzatishlar:     {rep['amended_questions_count']} ta")

    print("-" * 65)
    if res["has_updates"]:
        print(f"🔔 Yangi maʼlumotlar topildi! Sinxronlash uchun buyruq: python sync_questions.py --sync")
    else:
        print("Baza to‘liq yangilangan va eng so‘nggi holatda turibdi.")

def run_sync(service: QuestionSyncService, source: str = "all", ticket: int = None):
    print(f"🚀 [{datetime.now().strftime('%H:%M:%S')}] Savollarni sinxronizatsiya qilish boshlandi...")
    if source == "all":
        res = service.sync_all()
        print("\nSinxronizatsiya Yakunlandi:")
        print(f"  • Yangi qo‘shilgan kanonik savollar: {res['total_new_canonical_questions']} ta")
        print(f"  • Kiritilgan tuzatishlar:             {res['total_amendments_applied']} ta")
        print(f"  • Yangi yuklangan rasmlar:           {res['total_new_images']} ta")
        print(f"  • Jami yangilangan savollar soni:    {res['updated_db_metrics']['canonical_questions']} ta")
    else:
        target = [ticket] if ticket else None
        res = service.sync_source(source, target_tickets=target)
        print(f"\n[{source.upper()}] Sinxronizatsiya Yakunlandi:")
        print(f"  • Zaxira nusxa:                      {res.get('backup_created')}")
        print(f"  • Yangi qo‘shilgan kanonik savollar: {res.get('new_canonical_questions', 0)} ta")
        print(f"  • Yangi tarjimalar:                  {res.get('new_translations_added', 0)} ta")
        print(f"  • Yangi rasmlar:                     {res.get('new_images_acquired', 0)} ta")
        if res.get("errors"):
            print(f"  • Xatoliklar: {res['errors']}")

def main():
    parser = argparse.ArgumentParser(description="RULLY Question Sync & Source Monitor CLI")
    parser.add_argument("--status", action="store_true", help="Manbalar va bazaning hozirgi holatini ko‘rsatish")
    parser.add_argument("--check", action="store_true", help="Yangi savollar bor-yo‘qligini tekshirish (Dry-run)")
    parser.add_argument("--sync", action="store_true", help="Manbalardagi yangi savollarni bazaga yuklash")
    parser.add_argument("--source", type=str, default="all", choices=["all", "yesprava", "propdd"], help="Manbani tanlash")
    parser.add_argument("--ticket", type=int, default=None, help="Muayyan bilet raqamini sinxronlash")

    args = parser.parse_args()
    service = QuestionSyncService()

    if args.status or (not args.check and not args.sync):
        format_status(service)
    elif args.check:
        run_check(service, source=args.source)
    elif args.sync:
        run_sync(service, source=args.source, ticket=args.ticket)

if __name__ == "__main__":
    main()
