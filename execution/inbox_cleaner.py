"""
Inbox Cleaner — Tự động phân loại và dọn dẹp hòm thư Gmail
Hỗ trợ IMAP qua Gmail App Password.
"""

from __future__ import annotations
import argparse
import email
from email.header import decode_header
import imaplib
import json
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

UNREAD_FILE = DATA_DIR / "inbox_unread.json"
CLASSIFIED_FILE = DATA_DIR / "inbox_classified.json"


def decode_str(header_val: Any) -> str:
    """Giải mã tiêu đề email UTF-8 / Base64 chuẩn xác."""
    if not header_val:
        return ""
    decoded_list = decode_header(header_val)
    result = []
    for text, encoding in decoded_list:
        if isinstance(text, bytes):
            try:
                result.append(text.decode(encoding or "utf-8", errors="ignore"))
            except Exception:
                result.append(text.decode("latin-1", errors="ignore"))
        else:
            result.append(str(text))
    return "".join(result)


def get_imap_connection():
    """Kết nối tới máy chủ Gmail IMAP."""
    email_user = os.getenv("EMAIL_RECEIVER") or os.getenv("EMAIL_SENDER") or "hoangduyhung.forwork@gmail.com"
    email_pass = os.getenv("EMAIL_PASSWORD") or "wpqh juxf rmcv znck"
    email_pass = email_pass.replace(" ", "")

    print(f"📡 Đang kết nối tới Gmail ({email_user})...")
    mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
    mail.login(email_user, email_pass)
    return mail


# ==============================================================================
# Bước 1: Fetch Unread Emails
# ==============================================================================
def fetch_unread_emails(max_emails: int = 50) -> List[Dict[str, Any]]:
    """Lấy danh sách email chưa đọc từ hộp thư Đến (INBOX)."""
    mail = get_imap_connection()
    mail.select("INBOX")

    status, messages = mail.search(None, "UNSEEN")
    if status != "OK" or not messages[0]:
        print("🎉 Tuyệt vời! Hòm thư của bạn hiện tại không có email nào chưa đọc.")
        UNREAD_FILE.write_text("[]", encoding="utf-8")
        return []

    mail_ids = messages[0].split()
    total_unread = len(mail_ids)
    print(f"📬 Tìm thấy {total_unread} email chưa đọc. Đang tải chi tiết {min(total_unread, max_emails)} email gần nhất...")

    emails_data = []
    # Lấy từ email mới nhất trở về trước
    for mail_id in reversed(mail_ids[-max_emails:]):
        id_str = mail_id.decode("utf-8")
        status, data = mail.fetch(mail_id, "(RFC822.HEADER BODY.PEEK[TEXT])")
        if status != "OK":
            continue

        raw_email = None
        for response_part in data:
            if isinstance(response_part, tuple):
                raw_email = response_part[1]
                break

        if not raw_email:
            continue

        msg = email.message_from_bytes(raw_email)
        subject = decode_str(msg.get("Subject"))
        sender = decode_str(msg.get("From"))
        date = decode_str(msg.get("Date"))

        # Trích xuất đoạn text ngắn
        snippet = ""
        try:
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    if content_type == "text/plain":
                        payload = part.get_payload(decode=True)
                        if payload:
                            snippet = payload.decode("utf-8", errors="ignore")[:300]
                            break
            else:
                payload = msg.get_payload(decode=True)
                if payload:
                    snippet = payload.decode("utf-8", errors="ignore")[:300]
        except Exception:
            snippet = ""

        # Dọn dẹp snippet
        snippet = re.sub(r"\s+", " ", snippet).strip()

        emails_data.append({
            "id": id_str,
            "sender": sender,
            "subject": subject,
            "date": date,
            "snippet": snippet
        })

    mail.close()
    mail.logout()

    UNREAD_FILE.write_text(json.dumps(emails_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ Đã lưu danh sách {len(emails_data)} email chưa đọc vào: {UNREAD_FILE}")
    return emails_data


# ==============================================================================
# Bước 2: Classify Emails
# ==============================================================================
def classify_emails() -> List[Dict[str, Any]]:
    """Phân loại email: Quan trọng (Important) vs Không quan trọng (Not Important)."""
    if not UNREAD_FILE.exists():
        print("❌ Chưa có dữ liệu email chưa đọc. Vui lòng chạy lệnh --fetch trước.")
        return []

    unread_emails = json.loads(UNREAD_FILE.read_text(encoding="utf-8"))
    if not unread_emails:
        print("Không có email nào cần phân loại.")
        return []

    print(f"🤖 Đang phân tích và phân loại {len(unread_emails)} email...")

    automated_senders = [
        "no-reply", "noreply", "notifications@", "notification@", "newsletter",
        "updates@", "promo@", "marketing@", "digest@", "service@", "billing@",
        "security@", "alert@", "mailer-daemon", "support@github.com", "accounts.google.com",
        "team@", "info@", "news@", "community@", "do_not_reply@", "samsung.com",
        "vietcombank.com.vn", "quizizz.com", "binance.com", "duolingo.com", "canva.com"
    ]
    automated_keywords = [
        "unsubscribe", "hủy đăng ký", "newsletter", "digest", "verification code",
        "mã xác nhận", "mã otp", "xác thực tài khoản", "statement", "hóa đơn",
        "security alert", "cảnh báo bảo mật", "chào mừng bạn", "welcome to",
        "weekly digest", "daily digest", "kính gửi quý khách", "ưu đãi", "khuyến mãi",
        "đăng nhập mới", "new sign-in", "[qc]", "biên lai chuyển tiền", "thông báo giao dịch",
        "sale", "voucher", "deal", "quảng cáo"
    ]

    classified = []
    for item in unread_emails:
        sender_lower = item["sender"].lower()
        subject_lower = item["subject"].lower()
        snippet_lower = item["snippet"].lower()

        is_auto = False
        reason = ""

        # 1. Kiểm tra người gửi tự động
        for auto_sender in automated_senders:
            if auto_sender in sender_lower:
                is_auto = True
                reason = f"Hệ thống tự động ({auto_sender})"
                break

        # 2. Kiểm tra từ khóa newsletter / quảng cáo
        if not is_auto:
            for kw in automated_keywords:
                if kw in subject_lower or kw in snippet_lower:
                    is_auto = True
                    reason = f"Chứa nội dung thông báo/quảng cáo ('{kw}')"
                    break

        if is_auto:
            status = "not_important"
        else:
            status = "important"
            reason = "Thư cá nhân / Trao đổi trực tiếp"

        classified.append({
            "id": item["id"],
            "sender": item["sender"],
            "subject": item["subject"],
            "date": item["date"],
            "snippet": item["snippet"][:150],
            "classification": status,
            "reason": reason
        })

    CLASSIFIED_FILE.write_text(json.dumps(classified, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ Đã phân loại xong {len(classified)} email và lưu vào: {CLASSIFIED_FILE}")
    return classified


# ==============================================================================
# Bước 3: Review Classification
# ==============================================================================
def review_classification():
    """Hiển thị kết quả phân loại trước khi thực hiện đánh dấu đã đọc."""
    if not CLASSIFIED_FILE.exists():
        print("❌ Chưa có dữ liệu phân loại. Vui lòng chạy lệnh --classify trước.")
        return

    classified = json.loads(CLASSIFIED_FILE.read_text(encoding="utf-8"))
    if not classified:
        print("Hộp thư trống.")
        return

    important = [e for e in classified if e["classification"] == "important"]
    not_important = [e for e in classified if e["classification"] == "not_important"]

    print("\n" + "=" * 75)
    print("📊 BẢNG TỔNG KẾT PHÂN LOẠI EMAIL")
    print("=" * 75)
    print(f"🟢 [GIỮ LẠI - CHƯA ĐỌC] CÓ {len(important)} EMAIL QUAN TRỌNG:")
    if not important:
        print("   (Không có email cá nhân quan trọng nào)")
    else:
        for idx, e in enumerate(important, 1):
            print(f"   {idx}. Từ: {e['sender']}")
            print(f"      Tiêu đề: {e['subject']}")
            print(f"      👉 Lý do: {e['reason']}")

    print("\n" + "-" * 75)
    print(f"🔴 [SẼ ĐÁNH DẤU ĐÃ ĐỌC] CÓ {len(not_important)} EMAIL RÁC / THÔNG BÁO TỰ ĐỘNG:")
    if not not_important:
        print("   (Không có email rác)")
    else:
        for idx, e in enumerate(not_important, 1):
            print(f"   {idx}. Từ: {e['sender']}")
            print(f"      Tiêu đề: {e['subject']}")
            print(f"      👉 Lý do: {e['reason']}")
    print("=" * 75 + "\n")


# ==============================================================================
# Bước 4: Mark as Read
# ==============================================================================
def mark_not_important_as_read():
    """Đánh dấu tất cả email không quan trọng thành Đã Đọc."""
    if not CLASSIFIED_FILE.exists():
        print("❌ Chưa có dữ liệu phân loại. Vui lòng chạy lệnh --classify trước.")
        return

    classified = json.loads(CLASSIFIED_FILE.read_text(encoding="utf-8"))
    to_mark = [e for e in classified if e["classification"] == "not_important"]

    if not to_mark:
        print("✨ Không có email nào cần đánh dấu đã đọc!")
        return

    mail = get_imap_connection()
    mail.select("INBOX")

    id_list = ",".join([str(item["id"]) for item in to_mark])
    print(f"🧹 Đang đánh dấu ĐÃ ĐỌC siêu tốc cho {len(to_mark)} email...")
    mail.store(id_list, "+FLAGS", "\\Seen")

    mail.expunge()
    mail.close()
    mail.logout()

    print(f"🎉 HOÀN TẤT! Đã dọn dẹp và đánh dấu đã đọc cho {len(to_mark)} email thành công.")


# ==============================================================================
# CLI Entrypoint
# ==============================================================================
def main():
    parser = argparse.ArgumentParser(description="Inbox Cleaner — AI-Powered Email Triage")
    parser.add_argument("--fetch", action="store_true", help="Lấy danh sách email chưa đọc")
    parser.add_argument("--classify", action="store_true", help="Phân loại email quan trọng vs không quan trọng")
    parser.add_argument("--review", action="store_true", help="Xem trước danh sách phân loại")
    parser.add_argument("--mark-read", action="store_true", help="Đánh dấu đã đọc cho email không quan trọng")
    parser.add_argument("--all", action="store_true", help="Chạy toàn bộ quy trình")
    args = parser.parse_args()

    if args.all:
        fetch_unread_emails()
        classify_emails()
        review_classification()
        mark_not_important_as_read()
    elif args.fetch:
        fetch_unread_emails()
    elif args.classify:
        classify_emails()
    elif args.review:
        review_classification()
    elif args.mark_read:
        mark_not_important_as_read()
    else:
        fetch_unread_emails()
        classify_emails()
        review_classification()


if __name__ == "__main__":
    main()
