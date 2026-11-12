# AquaTwin-X

AquaTwin-X là hệ thống Digital Twin tích hợp thuật toán tối ưu để mô phỏng sự cố và hỗ trợ lựa chọn phương án phục hồi mạng lưới cấp nước.

## Mục tiêu sản phẩm

- Đọc và trực quan hóa mạng cấp nước từ file EPANET INP.
- Mô phỏng rò rỉ hoặc hỏng đường ống bằng WNTR.
- Phân tích áp suất, lưu lượng, mức độ phục vụ và phạm vi ảnh hưởng.
- Tìm kiếm phương án đóng hoặc mở van bằng thuật toán tối ưu.
- So sánh trạng thái bình thường, sau sự cố và sau phục hồi.

## Công nghệ

- Backend: Python, FastAPI, WNTR, NumPy, Pandas và NetworkX.
- Optimization: baseline, exhaustive search trên không gian nhỏ và Genetic Algorithm.
- Frontend: React, Vite, Cytoscape.js và Recharts.
- Data: EPANET INP, benchmark water networks và các kịch bản do simulator tạo.

## Cấu trúc dự án

```text
aquatwin-x/
├── backend/       FastAPI và lớp điều phối nghiệp vụ
├── frontend/      Dashboard React
├── simulation/    Digital Twin, mạng và kịch bản
├── optimization/  Hàm mục tiêu và thuật toán tìm kiếm
├── data/          Dữ liệu benchmark và dữ liệu đã xử lý
└── docs/          Phân tích, thiết kế và báo cáo
```

## Chạy backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Kiểm tra API tại `http://localhost:8000/api/health` và tài liệu Swagger tại `http://localhost:8000/docs`.

## Chạy frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend mặc định chạy tại `http://localhost:5173`.

## Quy ước nhánh

- `main`: phiên bản đã tích hợp và chạy ổn định.
- `simulation`: mô phỏng WNTR và xử lý kịch bản.
- `optimization`: hàm mục tiêu và thuật toán tối ưu.
- `frontend`: dashboard và trực quan hóa mạng.

