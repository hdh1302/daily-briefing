# Project & Personal Configuration Rules (GEMINI.md)

Tệp này quy định phong cách làm việc, quy chuẩn viết code và các hướng dẫn riêng cho AI Agent trong workspace này.

---

## 1. Ngôn ngữ & Giao tiếp (Language & Communication)
- **Ngôn ngữ phản hồi**: Tiếng Việt (trừ khi có yêu cầu viết tài liệu/comment bằng tiếng Anh).
- **Phong cách giải thích**: Ngắn gọn, rõ ràng, tập trung vào giải pháp và logic chính.

## 2. Tiêu chuẩn & Phong cách Code (Coding Standards)
- **Cấu trúc code**: Module hóa, phân tách rõ ràng giữa logic nghiệp vụ (business logic) và giao diện (UI).
- **Quy ước đặt tên (Naming Conventions)**:
  - Biến và hàm: `camelCase` (đối với JS/TS) hoặc `snake_case` (đối với Python).
  - Lớp (Classes/Types/Interfaces): `PascalCase`.
  - Hằng số (Constants): `UPPER_SNAKE_CASE`.
- **Chú thích (Comments)**:
  - Thêm chú thích giải thích lý do (Why) thay vì chỉ mô tả lại code làm gì (What).
  - Giữ lại các chú thích và docstring hiện có khi refactor.

## 3. Quy trình thực hiện công việc (Workflow Guidelines)
- **Kiểm tra trước khi sửa**: Luôn đọc và hiểu cấu trúc file trước khi thay đổi.
- **Xử lý lỗi (Error Handling)**: Bắt lỗi chi tiết, có thông báo log rõ ràng và thân thiện với người dùng.
- **Bảo mật**: Không hardcode API key, password, credentials vào mã nguồn; sử dụng biến môi trường (`.env`).
