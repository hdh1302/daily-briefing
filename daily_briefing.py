"""
Hệ thống tự động thu thập tin tức Hot từ các nguồn báo lớn nhất thế giới:
The Economist, The Guardian, The Verge, TechCrunch, CNBC, MarketWatch, Adweek...
Phân tích theo 3 chủ đề: Tech, Finance, Marketing (mỗi chủ đề 2-3 tin hot nhất),
tóm tắt bằng Gemini AI và gửi báo cáo qua Email lúc 9h sáng.
"""

from __future__ import annotations
import argparse
from datetime import datetime, time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import json
import os
from pathlib import Path
import re
import smtplib
import ssl
from typing import Any, Dict, List, Optional
import urllib.error
import urllib.request

import dateutil.parser
from dotenv import load_dotenv
import feedparser
import pytz

load_dotenv()

# ==============================================================================
# 1. Cấu hình Nguồn Báo Uy Tín Hàng Đầu Thế Giới (Tier 1 Global Outlets)
# ==============================================================================
RSS_SOURCES = {
    "tech": [
        {"name": "The Verge", "url": "https://www.theverge.com/rss/index.xml"},
        {"name": "TechCrunch", "url": "https://techcrunch.com/feed/"},
        {"name": "The Guardian (Tech)", "url": "https://www.theguardian.com/technology/rss"},
        {"name": "Wired", "url": "https://www.wired.com/feed/rss"},
    ],
    "finance": [
        {"name": "The Guardian (Business)", "url": "https://www.theguardian.com/business/rss"},
        {"name": "The Economist (Finance)", "url": "https://www.economist.com/finance-and-economics/rss.xml"},
        {"name": "CNBC Finance", "url": "https://search.cnbc.com/rs/search/view.html?partnerId=2000&keywords=finance&sort=date"},
        {"name": "MarketWatch", "url": "https://feeds.content.dowjones.io/public/rss/mw_topstories"},
    ],
    "marketing": [
        {"name": "Marketing Dive", "url": "https://www.marketingdive.com/feeds/news/"},
        {"name": "Adweek", "url": "https://www.adweek.com/feed/"},
        {"name": "Social Media Today", "url": "https://www.socialmediatoday.com/feeds/news/"},
        {"name": "The Drum", "url": "https://www.thedrum.com/rss/news"},
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
    """Xóa bỏ các thẻ HTML rác khỏi đoạn tóm tắt RSS để AI đọc rõ ràng."""
    clean = re.sub(r"<[^>]+>", " ", raw_html)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean[:400]


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
                        "pub_time_obj": pub_time
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
# 3. Module Tóm Tắt Tin Tức Bằng Gemini AI
# ==============================================================================
def summarize_with_gemini(
    tech_news: List[Dict[str, Any]],
    finance_news: List[Dict[str, Any]],
    marketing_news: List[Dict[str, Any]]
) -> Dict[str, str]:
    """
    Sử dụng Gemini API để phân tích, đối chiếu và tóm tắt thành bản tin chất lượng cao.
    """
    api_key = (os.getenv("GEMINI_API_KEY") or "").strip()
    if not api_key:
        print("[Lưu ý] Chưa thiết lập GEMINI_API_KEY.")
        return {
            "ai_analysis": "<i>(Chưa cấu hình GEMINI_API_KEY để phân tích AI chuyên sâu)</i>"
        }

    prompt = f"""
Bạn là một chuyên gia phân tích công nghệ, chiến lược tài chính và marketing cao cấp.
Dưới đây là các tin tức NỔI BẬT NHẤT (Hot News) từ các nguồn báo lớn nhất thế giới (The Economist, The Guardian, The Verge, TechCrunch, Adweek, CNBC...) trong đêm qua.

Nhiệm vụ của bạn là tổng hợp và viết bản tóm tắt buổi sáng (Morning Executive Briefing) bằng tiếng Việt cực kỳ sắc bén, ngắn gọn và có chiều sâu.

--- DỮ LIỆU TIN TỨC HOT ---

[CHỦ ĐỀ 1: CÔNG NGHỆ & AI (TECH)]
{chr(10).join([f"- [{a['source']}] {a['title']}: {a['summary']}" for a in tech_news]) or "Không có bài viết mới trong khung giờ."}

[CHỦ ĐỀ 2: TÀI CHÍNH & KINH TẾ (FINANCE)]
{chr(10).join([f"- [{a['source']}] {a['title']}: {a['summary']}" for a in finance_news]) or "Không có bài viết mới trong khung giờ."}

[CHỦ ĐỀ 3: MARKETING, THƯƠNG HIỆU & TRUYỀN THÔNG (MARKETING)]
{chr(10).join([f"- [{a['source']}] {a['title']}: {a['summary']}" for a in marketing_news]) or "Không có bài viết mới trong khung giờ."}

--- YÊU CẦU ĐỊNH DẠNG XUẤT BẢN ---
Hãy trình bày theo cấu trúc sau (dùng tiếng Việt chuẩn, chuyên nghiệp):

### ⚡ ĐIỂM TIN NỔI BẬT 60 GIÂY
(Tóm tắt 2-3 câu ngắn gọn về diễn biến nổi bật nhất của đêm qua)

### 💻 TECH & AI
(Tóm tắt 2-3 ý chính của các tin công nghệ hot, nêu rõ tên nguồn báo/hãng công nghệ, gạch đầu dòng kèm góc nhìn ngắn gọn)

### 📊 TÀI CHÍNH & THỊ TRƯỜNG
(Tóm tắt 2-3 ý chính về biến động thị trường, doanh nghiệp, dòng tiền từ The Economist/The Guardian/CNBC, gạch đầu dòng)

### 🚀 MARKETING & XU HƯỚNG
(Tóm tắt 2-3 ý chính về chiến dịch marketing, quảng cáo, mạng xã hội và bài học áp dụng, gạch đầu dòng)
"""

    debug_logs = []
    
    # 1. Gọi ListModels để lấy chính xác các model được hỗ trợ
    available_models = []
    for api_ver in ["v1beta", "v1"]:
        try:
            list_url = f"https://generativelanguage.googleapis.com/{api_ver}/models?key={api_key}"
            req = urllib.request.Request(list_url)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for item in data.get("models", []):
                    methods = item.get("supportedGenerationMethods", [])
                    if "generateContent" in methods:
                        m_name = item.get("name", "")
                        if m_name:
                            available_models.append((api_ver, m_name))
            if available_models:
                break
        except Exception as list_err:
            debug_logs.append(f"ListModels ({api_ver}) lỗi: {str(list_err)}")

    # 2. Sắp xếp ưu tiên: gemini-3.6-flash / 3.5-flash -> flash -> pro -> loại bỏ TTS
    def model_priority(item):
        _, name = item
        name_lower = name.lower()
        if "tts" in name_lower or "audio" in name_lower or "embed" in name_lower:
            return 99
        if "3.6-flash" in name_lower:
            return 1
        if "3.5-flash" in name_lower or "3-flash" in name_lower:
            return 2
        if "3.6-pro" in name_lower or "3.5-pro" in name_lower:
            return 3
        if "flash" in name_lower:
            return 4
        if "pro" in name_lower:
            return 5
        return 6

    valid_models = [m for m in available_models if "tts" not in m[1].lower() and "embed" not in m[1].lower()]
    sorted_models = sorted(valid_models, key=model_priority)
    
    hardcoded_priority = [
        ("v1beta", "models/gemini-3.6-flash"),
        ("v1beta", "models/gemini-3.5-flash"),
        ("v1beta", "models/gemini-3.0-flash"),
        ("v1beta", "models/gemini-3.6-pro"),
        ("v1beta", "models/gemini-3.5-pro"),
    ]
    
    final_models = []
    seen = set()
    for item in hardcoded_priority + sorted_models:
        if item[1] not in seen:
            seen.add(item[1])
            final_models.append(item)

    # 3. Thử gọi generateContent
    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}]
    }).encode("utf-8")

    for api_ver, full_model_name in final_models:
        url = f"https://generativelanguage.googleapis.com/{api_ver}/{full_model_name}:generateContent?key={api_key}"
        try:
            print(f"-> Đang gửi yêu cầu tóm tắt đến: {full_model_name} ({api_ver})...")
            req = urllib.request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=45) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                candidates = res_data.get("candidates", [])
                if candidates:
                    content_parts = candidates[0].get("content", {}).get("parts", [])
                    if content_parts:
                        text = content_parts[0].get("text", "")
                        if text:
                            print(f"✨ Thành công với {full_model_name}!")
                            return {"ai_analysis": text}
        except urllib.error.HTTPError as http_err:
            err_body = http_err.read().decode("utf-8", errors="ignore")
            debug_logs.append(f"HTTP {http_err.code} ({full_model_name}): {err_body[:150]}")
            print(f"   [Lỗi HTTP {http_err.code}]: {err_body}")
        except Exception as req_err:
            debug_logs.append(f"Lỗi ({full_model_name}): {str(req_err)}")

    details_text = "<br>".join(debug_logs[:5]) if debug_logs else "Không nhận được phản hồi từ Google."
    return {
        "ai_analysis": f"<strong>Chưa lấy được tóm tắt AI.</strong><br><br><span style='font-size:12px; color:#b91c1c;'>Chi tiết từ Google API:<br>{details_text}</span>"
    }


# ==============================================================================
# 4. Giao diện Email HTML Hiện Đại (3 Chuyên Mục)
# ==============================================================================
def generate_html_email(
    date_str: str,
    ai_content: Dict[str, str],
    tech_articles: List[Dict[str, Any]],
    finance_articles: List[Dict[str, Any]],
    marketing_articles: List[Dict[str, Any]]
) -> str:
    """Tạo template email HTML hiện đại, phân nhóm 3 chuyên mục Tech, Finance, Marketing."""
    
    raw_ai_text = ai_content.get("ai_analysis", "")
    ai_formatted = raw_ai_text
    ai_formatted = re.sub(r'###\s*(.*?)\n', r'<h3 style="color: #1e3a8a; margin: 16px 0 6px 0; font-size: 15px; font-weight: 700; border-bottom: 1px dashed #cbd5e1; padding-bottom: 4px;">\1</h3>', ai_formatted)
    ai_formatted = re.sub(r'##\s*(.*?)\n', r'<h2 style="color: #1e3a8a; margin: 18px 0 8px 0; font-size: 16px; font-weight: 800;">\1</h2>', ai_formatted)
    ai_formatted = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', ai_formatted)
    ai_formatted = re.sub(r'^\s*[-*]\s*(.*?)$', r'<li style="margin-bottom: 8px; line-height: 1.5;">\1</li>', ai_formatted, flags=re.MULTILINE)
    ai_formatted = ai_formatted.replace("\n\n", "<br><br>").replace("\n", "<br>")
    ai_analysis_html = ai_formatted
    
    def render_article_list(items: List[Dict[str, Any]], accent_color: str = "#2563eb") -> str:
        if not items:
            return "<p style='color: #64748b; font-style: italic; margin: 0 0 12px 0;'>Không có bài viết mới trong khung giờ này.</p>"
        html_cards = []
        for item in items:
            card = f"""
            <div style="background-color: #f8fafc; border-left: 4px solid {accent_color}; padding: 12px 16px; margin-bottom: 12px; border-radius: 6px;">
                <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; color: #64748b; margin-bottom: 4px; letter-spacing: 0.5px;">
                    {item['source']} • {item['published_at']}
                </div>
                <a href="{item['link']}" style="color: #0f172a; text-decoration: none; font-size: 15px; font-weight: 700; line-height: 1.4; display: block; margin-bottom: 6px;" target="_blank">
                    {item['title']} ↗
                </a>
                <div style="font-size: 13px; color: #475569; line-height: 1.5;">
                    {item['summary'][:220]}...
                </div>
            </div>
            """
            html_cards.append(card)
        return "".join(html_cards)

    tech_html = render_article_list(tech_articles, accent_color="#8b5cf6")     # Màu tím hiện đại cho Tech
    finance_html = render_article_list(finance_articles, accent_color="#0284c7") # Màu xanh dương cho Finance
    marketing_html = render_article_list(marketing_articles, accent_color="#f59e0b") # Màu cam năng động cho Marketing

    html = f"""
    <!DOCTYPE html>
    <html lang="vi">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Bản tin Buổi Sáng: Tech • Finance • Marketing</title>
    </head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f1f5f9; margin: 0; padding: 24px 12px; color: #1e293b;">
        <div style="max-width: 640px; margin: 0 auto; background-color: #ffffff; border-radius: 14px; overflow: hidden; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);">
            
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 50%, #0284c7 100%); color: #ffffff; padding: 36px 24px; text-align: center;">
                <div style="font-size: 12px; letter-spacing: 2px; text-transform: uppercase; opacity: 0.9; margin-bottom: 6px; font-weight: 600;">GLOBAL MORNING BRIEFING • {date_str}</div>
                <h1 style="margin: 0; font-size: 24px; font-weight: 900; line-height: 1.3; letter-spacing: -0.5px;">Điểm Tin Quốc Tế: Tech, Finance & Marketing</h1>
                <p style="margin: 8px 0 0 0; font-size: 13px; opacity: 0.85;">Từ các đầu báo hàng đầu: The Economist, The Guardian, The Verge, TechCrunch, Adweek...</p>
            </div>

            <div style="padding: 24px;">
                <!-- AI Executive Summary Box -->
                <div style="background-color: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 10px; padding: 20px; margin-bottom: 28px;">
                    <div style="display: flex; align-items: center; margin-bottom: 12px;">
                        <span style="font-size: 20px; margin-right: 8px;">✨</span>
                        <strong style="color: #166534; font-size: 16px; font-weight: 800;">Tóm Tắt & Phân Tích Thông Minh (Gemini AI)</strong>
                    </div>
                    <div style="font-size: 14px; line-height: 1.6; color: #1e293b;">
                        {ai_analysis_html}
                    </div>
                </div>

                <!-- 1. Tech Section -->
                <div style="margin-bottom: 28px;">
                    <div style="border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; margin-bottom: 14px; display: flex; align-items: center;">
                        <h2 style="font-size: 17px; font-weight: 800; color: #5b21b6; margin: 0;">💻 Công Nghệ & AI (The Verge, TechCrunch, Wired)</h2>
                    </div>
                    {tech_html}
                </div>

                <!-- 2. Finance Section -->
                <div style="margin-bottom: 28px;">
                    <div style="border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; margin-bottom: 14px; display: flex; align-items: center;">
                        <h2 style="font-size: 17px; font-weight: 800; color: #0369a1; margin: 0;">📊 Tài Chính & Kinh Tế (The Economist, The Guardian, CNBC)</h2>
                    </div>
                    {finance_html}
                </div>

                <!-- 3. Marketing Section -->
                <div style="margin-bottom: 24px;">
                    <div style="border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; margin-bottom: 14px; display: flex; align-items: center;">
                        <h2 style="font-size: 17px; font-weight: 800; color: #b45309; margin: 0;">🚀 Marketing & Truyền Thông (Adweek, Marketing Dive, Social Media Today)</h2>
                    </div>
                    {marketing_html}
                </div>
            </div>

            <!-- Footer -->
            <div style="background-color: #f8fafc; border-top: 1px solid #e2e8f0; padding: 20px; text-align: center; font-size: 12px; color: #64748b;">
                <p style="margin: 0 0 4px 0;">Bản tin tự động gửi lúc 09:00 sáng hàng ngày bởi GitHub Actions & Gemini AI.</p>
                <p style="margin: 0;">Chúc bạn một ngày làm việc tràn đầy cảm hứng và hiệu quả! ☕</p>
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
# 5. Hàm Main & CLI Handler
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
    print("-> Đang quét tin Tech (The Verge, TechCrunch, The Guardian, Wired)...")
    tech_articles = fetch_articles("tech", start_time, end_time, force_all=args.force_all_hours, max_articles=3)
    print(f"   Tìm thấy {len(tech_articles)} bài viết Tech hot.")

    print("-> Đang quét tin Finance (The Economist, The Guardian, CNBC, MarketWatch)...")
    finance_articles = fetch_articles("finance", start_time, end_time, force_all=args.force_all_hours, max_articles=3)
    print(f"   Tìm thấy {len(finance_articles)} bài viết Finance hot.")

    print("-> Đang quét tin Marketing (Adweek, Marketing Dive, Social Media Today, The Drum)...")
    marketing_articles = fetch_articles("marketing", start_time, end_time, force_all=args.force_all_hours, max_articles=3)
    print(f"   Tìm thấy {len(marketing_articles)} bài viết Marketing hot.")

    # 2. Tóm tắt với Gemini AI
    print("-> Đang phân tích và tóm tắt với Gemini AI...")
    ai_content = summarize_with_gemini(tech_articles, finance_articles, marketing_articles)

    # 3. Tạo template HTML
    date_str = now_vn.strftime("%d/%m/%Y")
    html_content = generate_html_email(date_str, ai_content, tech_articles, finance_articles, marketing_articles)

    # 4. Xuất file preview nếu yêu cầu
    if args.preview or args.dry_run:
        preview_file = Path("preview_newsletter.html")
        with open(preview_file, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"📄 Đã xuất bản tin mẫu xem trước tại: {preview_file.resolve()}")

    # 5. Gửi email
    subject = f"☕ [Global Morning Briefing] Tech • Finance • Marketing - {date_str}"
    if args.dry_run:
        print("🔍 Chế độ Dry-Run: Đã hoàn tất xử lý.")
    else:
        send_email(subject, html_content)


if __name__ == "__main__":
    main()
