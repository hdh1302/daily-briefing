# ☕ Daily Finance & Marketing Briefing System

Hệ thống tự động quét các sự kiện, tin tức Tài chính & Marketing trên thế giới (diễn ra trong khung giờ **00:00 - 07:00 sáng** giờ Việt Nam), sử dụng **Gemini AI** để tóm tắt, phân tích và gửi báo cáo định dạng HTML sang trọng vào Email của bạn đúng **09:00 sáng** hàng ngày.

---

## 🌟 Tính Năng Nổi Bật
- **Hoàn toàn tự động & miễn phí:** Chạy trên GitHub Actions, không cần bật máy tính.
- **Nguồn tin uy tín thế giới:** CNBC, Yahoo Finance, MarketWatch, Marketing Dive, Social Media Today, TechCrunch,...
- **Lọc chuẩn thời gian:** Tự động lọc các bài đăng trong khoảng 00:00 - 07:00 (UTC+7).
- **Phân tích AI chuyên sâu:** Gemini tổng hợp các ý chính, rút ra góc nhìn và tác động bằng tiếng Việt.
- **Giao diện Email hiện đại:** Tối ưu hiển thị đẹp mắt trên cả điện thoại (Gmail, Apple Mail, Outlook).

---

## 🚀 Hướng Dẫn Cài Đặt và Triển Khai (Chỉ cần làm 1 lần)

### Bước 1: Chuẩn bị các khóa bảo mật (API Key & Mật khẩu ứng dụng)

1. **Lấy Gemini API Key (Miễn phí):**
   - Truy cập [Google AI Studio](https://aistudio.google.com/app/apikey).
   - Đăng nhập và nhấn **"Create API key"** -> Sao chép mã API key.

2. **Tạo App Password cho Gmail:**
   - Truy cập trang bảo mật tài khoản Google: [Google Account Security](https://myaccount.google.com/security).
   - Đảm bảo tài khoản đã bật **Xác minh 2 bước (2-Step Verification)**.
   - Tìm mục **Mật khẩu ứng dụng (App passwords)** (hoặc tìm kiếm "App passwords" trong cài đặt tài khoản Google).
   - Đặt tên ứng dụng là `Daily Briefing` và bấm **Tạo**.
   - Sao chép mật khẩu 16 ký tự vừa xuất hiện (ví dụ: `abcd efgh ijkl mnop`).

---

### Bước 2: Đưa dự án lên GitHub và Cấu hình Secrets

1. Tạo một repository mới trên [GitHub](https://github.com/new) (chế độ **Private** để bảo mật).
2. Đẩy mã nguồn từ máy của bạn lên repository này:
   ```bash
   git init
   git add .
   git commit -m "Khởi tạo hệ thống Daily Briefing"
   git branch -M main
   git remote add origin https://github.com/<tai-khoan-cua-ban>/<ten-repo>.git
   git push -u origin main
   ```
3. Trên trang GitHub Repository của bạn, vào:
   `Settings` -> `Secrets and variables` -> `Actions` -> nhấn **New repository secret**.
4. Thêm lần lượt 4 biến bí mật sau:
   - `EMAIL_SENDER`: Địa chỉ Gmail dùng để gửi (ví dụ: `your_email@gmail.com`).
   - `EMAIL_PASSWORD`: Mật khẩu ứng dụng 16 ký tự vừa tạo ở Bước 1.
   - `EMAIL_RECEIVER`: Địa chỉ email nhận bản tin hàng ngày của bạn.
   - `GEMINI_API_KEY`: API Key lấy từ Google AI Studio.

---

### Bước 3: Kiểm tra và Chạy Thử

1. **Kiểm tra trên GitHub Actions:**
   - Vào tab **Actions** trên GitHub repository.
   - Chọn workflow **Daily Finance & Marketing Briefing**.
   - Bấm **Run workflow** -> **Run workflow** để kiểm tra gửi email ngay lập tức mà không cần đợi đến 9h sáng.
2. **Lịch tự động:**
   - Mỗi ngày đúng **09:00 sáng (giờ VN)**, GitHub Actions sẽ tự động chạy và gửi thư vào hòm thư của bạn.

---

## 🛠️ Chạy Thử Nghiệm Cục Bộ trên Máy Mac

Bạn có thể chạy thử nghiệm trực tiếp trên máy Mac:

```bash
# 1. Cài đặt thư viện
pip install -r requirements.txt

# 2. Tạo bản tin mẫu xem trước (không cần gửi email)
python daily_briefing.py --dry-run --force-all-hours --preview
```

Sau khi chạy lệnh trên, mở file `preview_newsletter.html` trên trình duyệt để chiêm ngưỡng giao diện bản tin email!
