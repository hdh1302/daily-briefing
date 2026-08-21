"""
Module hỗ trợ đọc đa định dạng tệp tin: Word, Excel, PDF, CSV, JSON, TXT.
Được thiết kế theo cấu trúc module hóa, dễ dàng mở rộng và tái sử dụng.
"""

from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import csv
import json

# Cài đặt các thư viện phụ thuộc nếu chưa có:
# pip install python-docx pandas openpyxl pypdf


class DocumentReader:
    """Lớp xử lý đọc nội dung từ nhiều định dạng tệp khác nhau."""

    @staticmethod
    def read_text(file_path: Union[str, Path]) -> str:
        """Đọc tệp văn bản thuần (.txt, .md, .log,...)."""
        path = Path(file_path)
        # Sử dụng encoding utf-8 để hỗ trợ tiếng Việt có dấu đầy đủ
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()

    @staticmethod
    def read_json(file_path: Union[str, Path]) -> Any:
        """Đọc và parse dữ liệu từ tệp JSON."""
        path = Path(file_path)
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def read_csv(file_path: Union[str, Path]) -> List[Dict[str, str]]:
        """Đọc tệp CSV và trả về danh sách các hàng dưới dạng Dict (cột -> giá trị)."""
        path = Path(file_path)
        with open(path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            return list(reader)

    @staticmethod
    def read_word(file_path: Union[str, Path]) -> str:
        """
        Đọc nội dung văn bản từ tệp Word (.docx).
        Cần cài đặt: pip install python-docx
        """
        try:
            import docx
        except ImportError:
            raise ImportError(
                "Vui lòng cài đặt thư viện 'python-docx' bằng lệnh: pip install python-docx"
            )

        doc = docx.Document(file_path)
        # Nối các đoạn văn bản (paragraphs) lại với nhau
        full_text = [para.text for para in doc.paragraphs if para.text.strip()]
        return "\n".join(full_text)

    @staticmethod
    def read_excel(file_path: Union[str, Path], sheet_name: Optional[Union[str, int]] = 0) -> Any:
        """
        Đọc dữ liệu bảng tính từ tệp Excel (.xlsx, .xls).
        Cần cài đặt: pip install pandas openpyxl
        """
        try:
            import pandas as pd
        except ImportError:
            raise ImportError(
                "Vui lòng cài đặt 'pandas' và 'openpyxl' bằng lệnh: pip install pandas openpyxl"
            )

        # Trả về DataFrame của pandas để dễ dàng thao tác, lọc hoặc chuyển sang dict/json
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        return df

    @staticmethod
    def read_pdf(file_path: Union[str, Path]) -> str:
        """
        Đọc nội dung văn bản từ tệp PDF (.pdf).
        Cần cài đặt: pip install pypdf
        """
        try:
            import pypdf
        except ImportError:
            raise ImportError(
                "Vui lòng cài đặt thư viện 'pypdf' bằng lệnh: pip install pypdf"
            )

        reader = pypdf.PdfReader(file_path)
        pages_text = []
        for index, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                pages_text.append(f"--- Trang {index + 1} ---\n{text}")
        return "\n\n".join(pages_text)

    @classmethod
    def auto_read(cls, file_path: Union[str, Path]) -> Any:
        """
        Tự động nhận diện định dạng file dựa vào phần mở rộng và gọi hàm đọc tương ứng.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Không tìm thấy tệp tin: {file_path}")

        suffix = path.suffix.lower()

        handlers = {
            ".txt": cls.read_text,
            ".md": cls.read_text,
            ".log": cls.read_text,
            ".json": cls.read_json,
            ".csv": cls.read_csv,
            ".docx": cls.read_word,
            ".xlsx": cls.read_excel,
            ".xls": cls.read_excel,
            ".pdf": cls.read_pdf,
        }

        handler = handlers.get(suffix)
        if not handler:
            raise ValueError(f"Định dạng tệp '{suffix}' hiện chưa được hỗ trợ.")

        return handler(path)


# ==========================================
# Ví dụ sử dụng (Usage Example)
# ==========================================
if __name__ == "__main__":
    print("=== Trình đọc đa định dạng tệp tin ===")
    
    # 1. Thử nghiệm với file TXT/MD có sẵn
    example_md = Path("GEMINI.md")
    if example_md.exists():
        content = DocumentReader.auto_read(example_md)
        print(f"\n[Đọc tự động file {example_md.name}]:")
        print(content[:200] + "...\n(Đã rút gọn hiển thị)")

    # 2. Hướng dẫn đọc các định dạng khác
    print("\n--- Hướng dẫn gọi hàm cho các định dạng khác ---")
    print("• Word : content = DocumentReader.read_word('tai_lieu.docx')")
    print("• Excel: df = DocumentReader.read_excel('bang_tinh.xlsx')")
    print("• PDF  : text = DocumentReader.read_pdf('sach.pdf')")
    print("• CSV  : rows = DocumentReader.read_csv('du_lieu.csv')")
    print("• Tự động nhận diện: data = DocumentReader.auto_read('bat_ky_file_nao.ext')")
