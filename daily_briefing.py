"""
Hệ thống tự động thu thập tin tức Hot từ các nguồn báo lớn nhất thế giới:
- Tech: The Verge, TechCrunch
- Finance: Bloomberg, Reuters, Financial Times
- Marketing: Ad Age, Adweek, Marketing Week

Mỗi chủ đề lọc 2-3 bài hot nhất trong khung giờ 00:00 - 07:00 sáng (giờ VN)
và gửi bản tin trực tiếp qua Email lúc 09:00 sáng.
"""

from __future__ import annotations
import argparse
from datetime import datetime, time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
from pathlib import Path
import re
import smtplib
import ssl
from typing import Any, Dict, List, Optional
import urllib.request

import dateutil.parser
from dotenv import load_dotenv
import feedparser
import pytz

load_dotenv()

# ==============================================================================
# 1. Cấu hình Nguồn Báo Uy Tín Hàng Đầu Thế Giới
# ==============================================================================
RSS_SOURCES = {
    "tech": [
        {"name": "The Verge", "url": "https://www.theverge.com/rss/index.xml"},
        {"name": "TechCrunch", "url": "https://techcrunch.com/feed/"},
    ],
    "finance": [
        {"name": "Bloomberg", "url": "https://feeds.bloomberg.com/markets/news.rss"},
        {"name": "Reuters", "url": "https://news.google.com/rss/search?q=site:reuters.com+business+OR+markets&hl=en-US&gl=US&ceid=US:en"},
        {"name": "Financial Times", "url": "https://www.ft.com/news-feed?format=rss"},
    ],
    "marketing": [
        {"name": "Ad Age", "url": "https://news.google.com/rss/search?q=site:adage.com&hl=en-US&gl=US&ceid=US:en"},
        {"name": "Adweek", "url": "https://www.adweek.com/feed/"},
        {"name": "Marketing Week", "url": "https://news.google.com/rss/search?q=site:marketingweek.com&hl=en-US&gl=US&ceid=US:en"},
    ],
}

TIMEZONE_VN = pytz.timezone("Asia/Ho_Chi_Minh")


# ==============================================================================
# 2. Module Thu thập & Lọc Tin Tức
# ==============================================================================
def parse_published_time(entry: Dict[str, Any]) -> Optional[datetime]:
    """Trích xuất và chuẩn hóa thời gian xuất bản của bài báo sang giờ VN."""
    raw_time = entry.get("published") or entry.get("updated") or entry.get("pubDate")
    if not raw_time and hasattr(entry, "published_parsed") and entry.published_parsed:
        import time as pytime
        dt = datetime.fromtimestamp(pytime.mktime(entry.published_parsed), tz=pytz.UTC)
        return dt.astimezone(TIMEZONE_VN)
    
    if raw_time:
        try:
            dt = dateutil.parser.parse(raw_time)
            if dt.tzinfo is None:
                dt = pytz.UTC.localize(dt)
            return dt.astimezone(TIMEZONE_VN)
        except Exception:
            return None
    return None


def clean_html_summary(raw_html: str) -> str:
    """Xóa bỏ các thẻ HTML rác khỏi đoạn tóm tắt RSS."""
    clean = re.sub(r"<[^>]+>", " ", raw_html)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean[:350]


def fetch_articles(category: str, start_time: datetime, end_time: datetime, force_all: bool = False, max_articles: int = 3) -> List[Dict[str, Any]]:
    """Thu thập bài viết từ các đầu báo lớn và chọn lọc 2-3 bài hot nhất."""
    articles = []
    sources = RSS_SOURCES.get(category, [])
    
    for source in sources:
        try:
            req = urllib.request.Request(
                source["url"],
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
            )
            with urllib.request.urlopen(req, timeout=12) as response:
                feed = feedparser.parse(response.read())
        except Exception as e:
            print(f"[Cảnh báo] Không thể tải feed {source['name']}: {e}")
            continue

        for entry in feed.entries:
            pub_time = parse_published_time(entry)
            is_valid_time = force_all or (pub_time and start_time <= pub_time <= end_time)
            
            if is_valid_time:
                title = entry.get("title", "").strip()
                raw_summary = entry.get("summary", "") or entry.get("description", "")
                summary = clean_html_summary(raw_summary)
                link = entry.get("link", "").strip()
                
                if title and link:
                    articles.append({
                        "source": source["name"],
                        "title": title,
                        "summary": summary,
                        "link": link,
                        "published_at": pub_time.strftime("%H:%M %d/%m/%Y") if pub_time else "Tin mới nhất",
                    })
    
    # Loại bỏ bài viết trùng lặp
    unique_articles = []
    seen = set()
    for art in articles:
        identifier = art["link"] or art["title"]
        if identifier not in seen:
            seen.add(identifier)
            unique_articles.append(art)
            
    # Lấy đúng số lượng bài hot nhất theo yêu cầu (2-3 bài mỗi chủ đề)
    return unique_articles[:max_articles]


# ==============================================================================
# 3. Giao diện Email HTML Tinh Tế & Hiện Đại
# ==============================================================================
def generate_html_email(
    date_str: str,
    tech_articles: List[Dict[str, Any]],
    finance_articles: List[Dict[str, Any]],
    marketing_articles: List[Dict[str, Any]]
) -> str:
    """Tạo template email HTML đẹp mắt, phân nhóm 3 chuyên mục Tech, Finance, Marketing."""
    
    def render_article_list(items: List[Dict[str, Any]], accent_color: str = "#2563eb", badge_color: str = "#eff6ff", badge_text: str = "#1d4ed8") -> str:
        if not items:
            return "<p style='color: #64748b; font-style: italic; margin: 0 0 12px 0;'>Không có bài viết mới trong khung giờ này.</p>"
        html_cards = []
        for item in items:
            card = f"""
            <div style="background-color: #ffffff; border: 1px solid #e2e8f0; border-left: 5px solid {accent_color}; padding: 16px; margin-bottom: 14px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
                <div style="margin-bottom: 8px;">
                    <span style="background-color: {badge_color}; color: {badge_text}; font-size: 11px; font-weight: 700; padding: 3px 8px; border-radius: 4px; text-transform: uppercase; letter-spacing: 0.5px;">
                        {item['source']}
                    </span>
                    <span style="font-size: 12px; color: #94a3b8; margin-left: 6px;">• {item['published_at']}</span>
                </div>
                <a href="{item['link']}" style="color: #0f172a; text-decoration: none; font-size: 16px; font-weight: 700; line-height: 1.4; display: block; margin-bottom: 8px;" target="_blank">
                    {item['title']} ↗
                </a>
                <div style="font-size: 13.5px; color: #475569; line-height: 1.6;">
                    {item['summary']}...
                </div>
            </div>
            """
            html_cards.append(card)
        return "".join(html_cards)

    tech_html = render_article_list(tech_articles, accent_color="#7c3aed", badge_color="#f5f3ff", badge_text="#6d28d9")
    finance_html = render_article_list(finance_articles, accent_color="#0284c7", badge_color="#f0f9ff", badge_text="#0369a1")
    marketing_html = render_article_list(marketing_articles, accent_color="#ea580c", badge_color="#fff7ed", badge_text="#c2410c")

    total_count = len(tech_articles) + len(finance_articles) + len(marketing_articles)

    html = f"""
    <!DOCTYPE html>
    <html lang="vi">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Điểm Tin Sáng: Tech • Finance • Marketing</title>
    </head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 24px 12px; color: #1e293b;">
        <div style="max-width: 650px; margin: 0 auto; background-color: #ffffff; border-radius: 14px; overflow: hidden; box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.08); border: 1px solid #e2e8f0;">
            
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 50%, #0369a1 100%); color: #ffffff; padding: 36px 24px; text-align: center;">
                <div style="font-size: 12px; letter-spacing: 2px; text-transform: uppercase; opacity: 0.9; margin-bottom: 6px; font-weight: 700;">DAILY BRIEFING • {date_str}</div>
                <h1 style="margin: 0; font-size: 25px; font-weight: 900; line-height: 1.3; letter-spacing: -0.5px;">Điểm Tin Thế Giới Buổi Sáng</h1>
                <p style="margin: 10px 0 0 0; font-size: 13.5px; opacity: 0.88; line-height: 1.5;">
                    Tổng hợp {total_count} tin nổi bật nhất diễn ra từ 00:00 - 07:00 sáng (Giờ Việt Nam)
                </p>
            </div>

            <!-- Overview Tag -->
            <div style="background-color: #f1f5f9; padding: 14px 24px; border-bottom: 1px solid #e2e8f0; font-size: 13px; color: #475569; display: flex; justify-content: space-between;">
                <span>📰 Nguồn tin: <strong>The Verge, TechCrunch, Bloomberg, Reuters, FT, Adweek, Ad Age, Marketing Week</strong></span>
            </div>

            <div style="padding: 24px; background-color: #f8fafc;">
                
                <!-- 1. Tech Section -->
                <div style="margin-bottom: 32px;">
                    <div style="border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; margin-bottom: 16px;">
                        <h2 style="font-size: 18px; font-weight: 800; color: #6d28d9; margin: 0;">💻 Công Nghệ & AI (The Verge, TechCrunch)</h2>
                    </div>
                    {tech_html}
                </div>

                <!-- 2. Finance Section -->
                <div style="margin-bottom: 32px;">
                    <div style="border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; margin-bottom: 16px;">
                        <h2 style="font-size: 18px; font-weight: 800; color: #0369a1; margin: 0;">📊 Tài Chính & Thị Trường (Bloomberg, Reuters, Financial Times)</h2>
                    </div>
                    {finance_html}
                </div>

                <!-- 3. Marketing Section -->
                <div style="margin-bottom: 24px;">
                    <div style="border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; margin-bottom: 16px;">
                        <h2 style="font-size: 18px; font-weight: 800; color: #c2410c; margin: 0;">🚀 Marketing & Thương Hiệu (Ad Age, Adweek, Marketing Week)</h2>
                    </div>
                    {marketing_html}
                </div>

            </div>

            <!-- Footer -->
            <div style="background-color: #ffffff; border-top: 1px solid #e2e8f0; padding: 22px; text-align: center; font-size: 12.5px; color: #64748b;">
                <p style="margin: 0 0 6px 0; font-weight: 600;">Bản tin tự động gửi vào lúc 09:00 sáng hàng ngày qua GitHub Actions.</p>
                <p style="margin: 0;">Chúc bạn một ngày làm việc tràn đầy năng lượng và hiệu quả! ☕🚀</p>
            </div>

        </div>
    </body>
    </html>
    """
    return html


def send_email(subject: str, html_content: str) -> None:
    """Gửi email qua giao thức SMTP SSL của Gmail."""
    sender = os.getenv("EMAIL_SENDER")
    password = os.getenv("EMAIL_PASSWORD")
    receiver = os.getenv("EMAIL_RECEIVER")

    if not all([sender, password, receiver]):
        raise ValueError("Thiếu cấu hình email trong biến môi trường (EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECEIVER).")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Global Morning Briefing <{sender}>"
    msg["To"] = receiver

    part = MIMEText(html_content, "html", "utf-8")
    msg.attach(part)

    context = ssl.create_default_context()
    print(f"Đang kết nối SMTP và gửi email đến {receiver}...")
    
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(sender, password.replace(" ", ""))
        server.sendmail(sender, receiver, msg.as_string())
        
    print("✅ Gửi email thành công!")


# ==============================================================================
# 4. Hàm Main & CLI Handler
# ==============================================================================
def main():
    parser = argparse.ArgumentParser(description="Thu thập tin tức sáng và gửi email.")
    parser.add_argument("--dry-run", action="store_true", help="Chạy thử không gửi email thực tế.")
    parser.add_argument("--preview", action="store_true", help="Lưu kết quả ra preview_newsletter.html.")
    parser.add_argument("--force-all-hours", action="store_true", help="Bỏ qua bộ lọc giờ 00:00-07:00 (dùng để test ban ngày).")
    args = parser.parse_args()

    now_vn = datetime.now(TIMEZONE_VN)
    today = now_vn.date()
    
    start_time = TIMEZONE_VN.localize(datetime.combine(today, time(0, 0, 0)))
    end_time = TIMEZONE_VN.localize(datetime.combine(today, time(7, 0, 0)))
    
    print(f"=== Bắt đầu tổng hợp tin tức ({now_vn.strftime('%d/%m/%Y %H:%M:%S')} VN) ===")
    if args.force_all_hours:
        print("⚡ Chế độ test: Lấy các tin hot mới nhất từ các đầu báo lớn.")
    else:
        print(f"🕒 Khung giờ lọc: {start_time.strftime('%H:%M')} đến {end_time.strftime('%H:%M')} ({today.strftime('%d/%m/%Y')})")

    # 1. Thu thập tin tức theo 3 chủ đề (mỗi chủ đề 2-3 bài hot nhất)
    print("-> Đang quét tin Tech (The Verge, TechCrunch)...")
    tech_articles = fetch_articles("tech", start_time, end_time, force_all=args.force_all_hours, max_articles=3)
    print(f"   Tìm thấy {len(tech_articles)} bài viết Tech hot.")

    print("-> Đang quét tin Finance (Bloomberg, Reuters, Financial Times)...")
    finance_articles = fetch_articles("finance", start_time, end_time, force_all=args.force_all_hours, max_articles=3)
    print(f"   Tìm thấy {len(finance_articles)} bài viết Finance hot.")

    print("-> Đang quét tin Marketing (Ad Age, Adweek, Marketing Week)...")
    marketing_articles = fetch_articles("marketing", start_time, end_time, force_all=args.force_all_hours, max_articles=3)
    print(f"   Tìm thấy {len(marketing_articles)} bài viết Marketing hot.")

    # 2. Tạo template HTML trực tiếp từ các bài báo
    date_str = now_vn.strftime("%d/%m/%Y")
    html_content = generate_html_email(date_str, tech_articles, finance_articles, marketing_articles)

    # 3. Xuất file preview nếu yêu cầu
    if args.preview or args.dry_run:
        preview_file = Path("preview_newsletter.html")
        with open(preview_file, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"📄 Đã xuất bản tin mẫu xem trước tại: {preview_file.resolve()}")

    # 4. Gửi email
    subject = f"☕ [Global Morning Briefing] Tech • Finance • Marketing - {date_str}"
    if args.dry_run:
        print("🔍 Chế độ Dry-Run: Đã hoàn tất xử lý.")
    else:
        send_email(subject, html_content)


if __name__ == "__main__":
    main()
