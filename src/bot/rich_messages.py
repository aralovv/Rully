"""
Telegram Rich Messages & Card Widget Formatting Layer.
Provides high-fidelity visual Card Widgets, container frames, badges,
expandable legal blockquotes, and 100% pure localized typography.
"""

import html
from typing import Dict, Any, List, Optional
from src.bot.strings import get_str
from src.bot.category_localization import localize_category, localize_legal_reference

def escape_html(text: Optional[str]) -> str:
    if not text:
        return ""
    return html.escape(str(text))

def build_progress_bar(current: int, total: int, length: int = 8) -> str:
    if total <= 0:
        return "⬜" * length
    filled = int(round((current / total) * length))
    filled = max(0, min(length, filled))
    return "🟩" * filled + "⬜" * (length - filled)

def format_rich_question(session_type: str, current_index: int, total_questions: int,
                          category_name: str, question_text: str,
                          options: List[Dict[str, Any]], language: str = "uz_latn",
                          time_remaining_seconds: Optional[int] = None,
                          feedback: Optional[Dict[str, Any]] = None,
                          show_explanation: bool = True,
                          max_caption_len: int = 1000) -> str:
    """
    Constructs a Rich Visual Card Widget for the question.
    Incorporates container frames, badges, localized category & citations,
    and expandable blockquotes.
    """
    # 1. Localize Category
    loc_cat = localize_category(category_name, language)

    # 2. Select Card Container Header
    if feedback:
        is_corr = feedback.get("is_correct", False)
        header_text = get_str("feedback_correct_header", language) if is_corr else get_str("feedback_incorrect_header", language)
    else:
        type_headers = {
            "EXAM": get_str("card_header_exam", language),
            "CUSTOM": get_str("card_header_custom", language),
            "CATEGORY": get_str("card_header_category", language),
            "QUICK": get_str("card_header_quick", language),
            "MISTAKES": get_str("card_header_mistakes", language)
        }
        header_text = type_headers.get(session_type, get_str("card_header_exam", language))

    # Visual Card Container Frame
    lines = [
        "╭──────────────────────────────╮",
        f"│  {header_text}",
        "╰──────────────────────────────╯"
    ]

    # Meta Badges
    q_badge = get_str("card_badge_question", language, current=current_index, total=total_questions)
    if time_remaining_seconds is not None and time_remaining_seconds > 0:
        mins = int(time_remaining_seconds // 60)
        secs = int(time_remaining_seconds % 60)
        t_badge = get_str("card_badge_time", language, mins=mins, secs=secs)
        lines.append(f"{q_badge}   {t_badge}")
    else:
        lines.append(q_badge)

    if loc_cat:
        lines.append(get_str("card_badge_category", language, category=escape_html(loc_cat)))

    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"❓ <b>{escape_html(question_text)}</b>")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    # Options presentation
    for opt in options:
        opt_key = opt["key"]
        opt_text = opt["text"].get(language, "") if isinstance(opt["text"], dict) else opt["text"]
        
        if feedback:
            selected_key = feedback.get("selected_key")
            correct_key = feedback.get("correct_key")
            if opt_key == correct_key:
                tag = f" {get_str('feedback_correct_tag', language)}"
                prefix = "✅"
            elif opt_key == selected_key and selected_key != correct_key:
                tag = f" {get_str('feedback_selected_wrong_tag', language)}"
                prefix = "❌"
            else:
                tag = ""
                prefix = "▫️"
            lines.append(f"{prefix} <b>[{opt_key}]</b> {escape_html(opt_text)}{tag}")
        else:
            lines.append(f"<b>[{opt_key}]</b> {escape_html(opt_text)}")

    # Feedback & Legal Citation Section
    if feedback and show_explanation:
        raw_lref = feedback.get("legal_reference")
        expl = feedback.get("explanation")
        
        loc_lref = localize_legal_reference(raw_lref, language) if raw_lref else ""

        if loc_lref or expl:
            lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            quote_parts = []
            if loc_lref:
                quote_parts.append(f"<b>{get_str('legal_reference_header', language)}</b> {escape_html(loc_lref)}")
            if expl:
                quote_parts.append(f"<b>{get_str('explanation_header', language)}</b> {escape_html(expl)}")

            quote_text = "\n".join(quote_parts)

            # Safeguard caption length for Telegram media
            full_card = "\n".join(lines) + f"\n<blockquote expandable>{quote_text}</blockquote>"
            if len(full_card) > max_caption_len:
                allowed_expl_len = max(50, max_caption_len - len("\n".join(lines)) - 100)
                truncated_quote = quote_text[:allowed_expl_len] + "..."
                lines.append(f"<blockquote expandable>{truncated_quote}</blockquote>")
            else:
                lines.append(f"<blockquote expandable>{quote_text}</blockquote>")

    return "\n".join(lines)


def format_rich_result(total: int, correct: int, incorrect: int,
                       time_spent_seconds: float, passed: bool,
                       category_breakdown: Dict[str, Any], language: str = "uz_latn",
                       unanswered: int = 0) -> str:
    """
    Constructs a Rich Visual Card Scorecard with localized breakdown.
    """
    title = get_str("result_passed_title", language) if passed else get_str("result_failed_title", language)
    status_str = get_str("status_passed", language) if passed else get_str("status_failed", language)
    
    pct = round((correct / total * 100), 1) if total > 0 else 0.0
    mins = int(time_spent_seconds // 60)
    secs = int(time_spent_seconds % 60)
    
    if language == "ru":
        time_str = f"{mins} мин {secs} сек" if mins > 0 else f"{secs} сек"
    elif language == "uz_cyrl":
        time_str = f"{mins} дақ {secs} сон" if mins > 0 else f"{secs} сон"
    else:
        time_str = f"{mins} daq {secs} son" if mins > 0 else f"{secs} son"

    summary_text = get_str("result_summary", language,
                           total=total, correct=correct, incorrect=incorrect,
                           percentage=pct, time_str=time_str, status_text=status_str)

    if unanswered > 0:
        if language == "ru":
            summary_text += f"\n• Без ответа: <b>{unanswered}</b>"
        elif language == "uz_cyrl":
            summary_text += f"\n• Жавобсиз: <b>{unanswered} та</b>"
        else:
            summary_text += f"\n• Javobsiz: <b>{unanswered} ta</b>"

    lines = [
        "╭──────────────────────────────╮",
        f"│  {title}",
        "╰──────────────────────────────╯",
        "",
        summary_text
    ]

    # Category breakdown table (100% localized!)
    if category_breakdown:
        breakdown_titles = {
            "uz_latn": ("📋 <b>Mavzular bo‘yicha tahlil:</b>", "Mavzu", "Natija"),
            "uz_cyrl": ("📋 <b>Бўлимлар бўйича таҳлил:</b>", "Бўлим", "Натижа"),
            "ru": ("📋 <b>Анализ по разделам:</b>", "Раздел", "Результат")
        }
        b_hdr, col_cat, col_res = breakdown_titles.get(language, breakdown_titles["uz_latn"])
        lines.append(b_hdr)
        lines.append("<pre>")
        lines.append(f"{col_cat:<24} | {col_res:<8}")
        lines.append("-" * 35)
        for cat_name, stats in list(category_breakdown.items())[:6]:
            loc_cat = localize_category(cat_name, language)
            short_name = loc_cat[:22] + ".." if len(loc_cat) > 22 else loc_cat
            c_cnt = stats.get("correct", 0)
            t_cnt = stats.get("total", 0)
            lines.append(f"{short_name:<24} | {c_cnt}/{t_cnt}")
        lines.append("</pre>")

    return "\n".join(lines)
