"""
Hệ thống tự động thu thập tin tức Tài chính & Marketing quốc tế,
tóm tắt bằng Gemini AI và gửi báo cáo qua Email lúc 9h sáng.
"""

from __future__ import annotations
import argparse
from datetime import datetime, time, timedelta
import email.message
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
from pathlib import Path
import smtplib
import ssl
from typing import Any, Dict, List, Optional
import urllib.request

import dateutil.parser
from dotenv import load_dotenv
import feedparser
import pytz

# Nạp biến môi trường từ .env (nếu chạy cục bộ)
load_dotenv()

# ==============================================================================
# 1. Cấu hình Nguồn tin (RSS Feeds)
# ==============================================================================
RSS_SOURCES = {
    "finance": [
        {"name": "CNBC Finance", "url": "https://search.cnbc.com/rs/search/view.html?partnerId=2000&keywords=finance&sort=date"},
        {"name": "CNBC Economy", "url": "https://search.cnbc.com/rs/search/view.html?partnerId=2000&keywords=economy&sort=date"},
        {"name": "Yahoo Finance", "url": "https://finance.yahoo.com/news/rssindex"},
        {"name": "MarketWatch Top Stories", "url": "https://feeds.content.dowjones.io/public/rss/mw_topstories"},
    ],
    "marketing": [
        {"name": "Marketing Dive", "url": "https://www.marketingdive.com/feeds/news/"},
        {"name": "Social Media Today", "url": "https://www.socialmediatoday.com/feeds/news/"},
        {"name": "Search Engine Journal", "url": "https://www.searchenginejournal.com/feed/"},
        {"name": "Adweek", "url": "https://www.adweek.com/feed/"},
        {"name": "TechCrunch", "url": "https://techcrunch.com/feed/"},
    ],
}

TIMEZONE_VN = pytz.timezone("Asia/Ho_Chi_Minh")


# ==============================================================================
# 2. Module Thu thập & Lọc Tin Tức theo Giờ Việt Nam
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


def fetch_articles(category: str, start_time: datetime, end_time: datetime, force_all: bool = False) -> List[Dict[str, Any]]:
    """Thu thập bài viết từ danh sách RSS và lọc theo khung thời gian."""
    articles = []
    sources = RSS_SOURCES.get(category, [])
    
    for source in sources:
        try:
            # Giả lập User-Agent để tránh bị một số trang chặn feed
            req = urllib.request.Request(
                source["url"],
                headers={"User-Agent": "Mozilla/5.0 (DailyNewsBot/1.0; +https://github.com)"}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                feed = feedparser.parse(response.read())
        except Exception as e:
            print(f"[Cảnh báo] Lỗi khi tải RSS từ {source['name']}: {e}")
            continue

        for entry in feed.entries:
            pub_time = parse_published_time(entry)
            
            # Lọc theo khung giờ hoặc lấy tất cả nếu force_all được bật
            is_valid_time = force_all or (pub_time and start_time <= pub_time <= end_time)
            
            if is_valid_time:
                title = entry.get("title", "").strip()
                summary = entry.get("summary", "") or entry.get("description", "")
                link = entry.get("link", "").strip()
                
                if title and link:
                    articles.append({
                        "source": source["name"],
                        "title": title,
                        "summary": summary[:400],  # Lấy tóm tắt ngắn ban đầu
                        "link": link,
                        "published_at": pub_time.strftime("%H:%M %d/%m/%Y") if pub_time else "Mới cập nhật"
                    })
    
    # Loại bỏ bài trùng lặp theo link hoặc tiêu đề
    unique_articles = []
    seen = set()
    for art in articles:
        identifier = art["link"] or art["title"]
        if identifier not in seen:
            seen.add(identifier)
            unique_articles.append(art)
            
    return unique_articles[:10]  # Giới hạn tối đa 10 tin nổi bật mỗi danh mục


# ==============================================================================
# 3. Module Tóm Tắt Tin Tức Bằng Gemini AI
# ==============================================================================
def summarize_with_gemini(finance_news: List[Dict[str, Any]], marketing_news: List[Dict[str, Any]]) -> Dict[str, str]:
    """
    Sử dụng Gemini API để tóm tắt, phân tích và dịch tin tức sang tiếng Việt chuyên sâu.
    """
    api_key = (os.getenv("GEMINI_API_KEY") or "").strip()
    if not api_key:
        print("[Lưu ý] Chưa thiết lập GEMINI_API_KEY. Sử dụng tóm tắt dự phòng từ nguồn RSS.")
        return {
            "ai_analysis": "<i>(Chưa cấu hình GEMINI_API_KEY để phân tích AI chuyên sâu)</i>"
        }

    prompt = f"""
Bạn là một chuyên gia phân tích tài chính quốc tế và chiến lược marketing cao cấp.
Nhiệm vụ của bạn là đọc các tin tức mới nhất diễn ra trên thế giới trong đêm qua và viết bản tóm tắt buổi sáng (Daily Briefing) cho một độc giả tại Việt Nam.

Dữ liệu tin tức thu thập được:

[PHẦN 1: TIN TỨC TÀI CHÍNH & KINH TẾ]
{chr(10).join([f"- {a['title']} (Nguồn: {a['source']}): {a['summary']}" for a in finance_news]) or "Không có tin mới trong khung giờ."}

[PHẦN 2: TIN TỨC MARKETING & CÔNG NGHỆ QUẢNG CÁO]
{chr(10).join([f"- {a['title']} (Nguồn: {a['source']}): {a['summary']}" for a in marketing_news]) or "Không có tin mới trong khung giờ."}

Yêu cầu xuất bản:
Hãy trả về bản tóm tắt bằng định dạng văn bản chuẩn, chia làm 3 phần rõ ràng:
1. [TỔNG QUAN NHANH]: 2-3 câu ngắn gọn tóm tắt bức tranh toàn cảnh đêm qua.
2. [TÀI CHÍNH - KINH TẾ]: Tóm tắt 3-5 điểm nhấn quan trọng nhất (kèm nhận định tác động ngắn gọn bằng tiếng Việt, gạch đầu dòng).
3. [MARKETING - TRUYỀN THÔNG]: Tóm tắt 3-5 xu hướng, chiến dịch hoặc tin tức nổi bật nhất (kèm bài học/gợi ý ngắn gọn bằng tiếng Việt, gạch đầu dòng).

Văn phong: Chuyên nghiệp, cô đọng, sắc bén, dễ đọc trên điện thoại vào buổi sáng.
"""

    debug_logs = []
    
    # Cách 1: Gọi qua REST API trực tiếp tới Google AI Studio (Chuẩn xác & Độc lập)
    import json
    models_to_try = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash-exp", "gemini-pro"]
    
    for model_name in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        payload = json.dumps({
            "contents": [{"parts": [{"text": prompt}]}]
        }).encode("utf-8")
        
        try:
            req = urllib.request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                candidates = data.get("candidates", [])
                if candidates:
                    text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                    if text:
                        print(f"✨ Thành công với model: {model_name}")
                        return {"ai_analysis": text}
        except urllib.error.HTTPError as http_err:
            err_body = http_err.read().decode("utf-8", errors="ignore")
            debug_logs.append(f"HTTP {http_err.code} ({model_name}): {err_body[:180]}")
            print(f"   [HTTP Error {http_err.code}]: {err_body}")
        except Exception as e:
            debug_logs.append(f"Lỗi ({model_name}): {str(e)}")

    # Cách 2: Thử qua SDK nếu REST chưa được
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        resp = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt
        )
        if resp and resp.text:
            return {"ai_analysis": resp.text}
    except Exception as e:
        debug_logs.append(f"SDK: {str(e)[:150]}")

    details_text = "<br>".join(debug_logs) if debug_logs else "Không nhận được phản hồi từ máy chủ Google."
    return {
        "ai_analysis": f"<strong>Chưa lấy được tóm tắt AI.</strong><br><br><span style='font-size:12px; color:#b91c1c;'>Chi tiết từ Google API:<br>{details_text}</span>"
    }


# ==============================================================================
# 4. Module Tạo Giao Diện Email HTML Sang Trọng & Gửi Thư
# ==============================================================================
def generate_html_email(
    date_str: str,
    ai_content: Dict[str, str],
    finance_articles: List[Dict[str, Any]],
    marketing_articles: List[Dict[str, Any]]
) -> str:
    """Tạo template email HTML hiện đại, chuẩn Responsive cho mobile và desktop."""
    
    raw_ai_text = ai_content.get("ai_analysis", "")
    # Chuyển đổi cơ bản các định dạng markdown phổ biến sang HTML
    import re
    ai_formatted = raw_ai_text
    ai_formatted = re.sub(r'###\s*(.*?)\n', r'<h3 style="color: #1e3a8a; margin: 12px 0 6px 0; font-size: 15px;">\1</h3>', ai_formatted)
    ai_formatted = re.sub(r'##\s*(.*?)\n', r'<h2 style="color: #1e3a8a; margin: 16px 0 8px 0; font-size: 16px;">\1</h2>', ai_formatted)
    ai_formatted = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', ai_formatted)
    ai_formatted = re.sub(r'^\s*[-*]\s*(.*?)$', r'<li style="margin-bottom: 6px;">\1</li>', ai_formatted, flags=re.MULTILINE)
    ai_formatted = ai_formatted.replace("\n\n", "<br><br>").replace("\n", "<br>")
    ai_analysis_html = ai_formatted
    
    def render_article_list(items: List[Dict[str, Any]]) -> str:
        if not items:
            return "<p style='color: #64748b; font-style: italic;'>Không có bài viết mới trong khung giờ này.</p>"
        html_cards = []
        for item in items:
            card = f"""
            <div style="background-color: #f8fafc; border-left: 4px solid #3b82f6; padding: 12px 16px; margin-bottom: 12px; border-radius: 4px;">
                <div style="font-size: 11px; font-weight: bold; text-transform: uppercase; color: #64748b; margin-bottom: 4px;">
                    {item['source']} • {item['published_at']}
                </div>
                <a href="{item['link']}" style="color: #0f172a; text-decoration: none; font-size: 15px; font-weight: 600; line-height: 1.4; display: block; margin-bottom: 6px;" target="_blank">
                    {item['title']} ↗
                </a>
                <div style="font-size: 13px; color: #475569; line-height: 1.5;">
                    {item['summary'][:200]}...
                </div>
            </div>
            """
            html_cards.append(card)
        return "".join(html_cards)

    finance_html = render_article_list(finance_articles)
    marketing_html = render_article_list(marketing_articles)

    html = f"""
    <!DOCTYPE html>
    <html lang="vi">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Bản tin Tài chính & Marketing Buổi sáng</title>
    </head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f1f5f9; margin: 0; padding: 24px 12px; color: #1e293b;">
        <div style="max-width: 640px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
            
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #1e3a8a 0%, #0284c7 100%); color: #ffffff; padding: 32px 24px; text-align: center;">
                <div style="font-size: 12px; letter-spacing: 2px; text-transform: uppercase; opacity: 0.9; margin-bottom: 6px;">MORNING BRIEFING • {date_str}</div>
                <h1 style="margin: 0; font-size: 24px; font-weight: 800; line-height: 1.3;">Điểm Tin Tài Chính & Marketing</h1>
                <p style="margin: 8px 0 0 0; font-size: 14px; opacity: 0.9;">Tổng hợp sự kiện thế giới từ 00:00 - 07:00 sáng (Giờ Việt Nam)</p>
            </div>

            <div style="padding: 24px;">
                <!-- AI Summary Box -->
                <div style="background-color: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px; padding: 20px; margin-bottom: 28px;">
                    <div style="display: flex; align-items: center; margin-bottom: 12px;">
                        <span style="font-size: 18px; margin-right: 8px;">✨</span>
                        <strong style="color: #1e40af; font-size: 16px;">Tóm tắt & Phân tích từ AI (Gemini)</strong>
                    </div>
                    <div style="font-size: 14px; line-height: 1.6; color: #1e293b;">
                        {ai_analysis_html}
                    </div>
                </div>

                <!-- Finance Section -->
                <div style="margin-bottom: 28px;">
                    <div style="border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; margin-bottom: 16px;">
                        <h2 style="font-size: 18px; font-weight: 700; color: #0f172a; margin: 0;">📊 Tài Chính & Kinh Tế Quốc Tế</h2>
                    </div>
                    {finance_html}
                </div>

                <!-- Marketing Section -->
                <div style="margin-bottom: 24px;">
                    <div style="border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; margin-bottom: 16px;">
                        <h2 style="font-size: 18px; font-weight: 700; color: #0f172a; margin: 0;">🚀 Marketing, Thương Hiệu & Tech</h2>
                    </div>
                    {marketing_html}
                </div>
            </div>

            <!-- Footer -->
            <div style="background-color: #f8fafc; border-top: 1px solid #e2e8f0; padding: 20px; text-align: center; font-size: 12px; color: #94a3b8;">
                <p style="margin: 0 0 4px 0;">Bản tin được tạo tự động bởi Antigravity & GitHub Actions vào lúc 09:00 sáng hàng ngày.</p>
                <p style="margin: 0;">Chúc bạn một ngày làm việc tràn đầy năng lượng và hiệu quả! ☕</p>
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
        raise ValueError("Thiếu thông tin cấu hình email trong biến môi trường (EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECEIVER).")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Morning Briefing <{sender}>"
    msg["To"] = receiver

    part = MIMEText(html_content, "html", "utf-8")
    msg.attach(part)

    context = ssl.create_default_context()
    print(f"Đang kết nối SMTP và gửi email đến {receiver}...")
    
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(sender, password.replace(" ", ""))  # Loại bỏ khoảng trắng nếu copy từ Google
        server.sendmail(sender, receiver, msg.as_string())
        
    print("✅ Gửi email thành công!")


# ==============================================================================
# 5. Hàm Main & CLI Handler
# ==============================================================================
def main():
    parser = argparse.ArgumentParser(description="Thu thập tin tức sáng và gửi email.")
    parser.add_argument("--dry-run", action="store_true", help="Chạy thử không gửi email thực tế.")
    parser.add_argument("--preview", action="store_true", help="Lưu kết quả ra preview_newsletter.html để xem trước.")
    parser.add_argument("--force-all-hours", action="store_true", help="Bỏ qua bộ lọc giờ 00:00-07:00 (dùng để test ban ngày).")
    args = parser.parse_args()

    now_vn = datetime.now(TIMEZONE_VN)
    today = now_vn.date()
    
    # Định nghĩa khoảng thời gian từ 00:00 đến 07:00 sáng hôm nay (giờ VN)
    start_time = TIMEZONE_VN.localize(datetime.combine(today, time(0, 0, 0)))
    end_time = TIMEZONE_VN.localize(datetime.combine(today, time(7, 0, 0)))
    
    print(f"=== Bắt đầu tổng hợp tin tức ({now_vn.strftime('%d/%m/%Y %H:%M:%S')} VN) ===")
    if args.force_all_hours:
        print("⚡ Chế độ test: Lấy các tin tức mới nhất bất kể giờ xuất bản.")
    else:
        print(f"🕒 Khung giờ lọc: {start_time.strftime('%H:%M')} đến {end_time.strftime('%H:%M')} ({today.strftime('%d/%m/%Y')})")

    # 1. Thu thập tin tức
    print("-> Đang quét tin Tài chính...")
    finance_articles = fetch_articles("finance", start_time, end_time, force_all=args.force_all_hours)
    print(f"   Tìm thấy {len(finance_articles)} bài viết tài chính.")

    print("-> Đang quét tin Marketing...")
    marketing_articles = fetch_articles("marketing", start_time, end_time, force_all=args.force_all_hours)
    print(f"   Tìm thấy {len(marketing_articles)} bài viết marketing.")

    # 2. Tóm tắt với Gemini AI
    print("-> Đang phân tích và tóm tắt với Gemini AI...")
    ai_content = summarize_with_gemini(finance_articles, marketing_articles)

    # 3. Tạo template HTML
    date_str = now_vn.strftime("%d/%m/%Y")
    html_content = generate_html_email(date_str, ai_content, finance_articles, marketing_articles)

    # 4. Xuất file preview nếu yêu cầu
    if args.preview or args.dry_run:
        preview_file = Path("preview_newsletter.html")
        with open(preview_file, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"📄 Đã xuất bản tin mẫu xem trước tại: {preview_file.resolve()}")

    # 5. Gửi email
    subject = f"☕ [Morning Briefing] Bản Tin Tài Chính & Marketing - {date_str}"
    if args.dry_run:
        print("🔍 Chế độ Dry-Run: Đã hoàn tất xử lý, bỏ qua bước gửi email.")
    else:
        send_email(subject, html_content)


if __name__ == "__main__":
    main()
