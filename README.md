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
python -m venv .venv
.venv\Scripts\activate
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload
```

Kiểm tra API tại `http://localhost:8000/api/health` và tài liệu Swagger tại `http://localhost:8000/docs`.

## Chạy mô phỏng đầu tiên

Từ thư mục gốc của dự án, kiểm tra metadata mạng demo.

```bash
python -m simulation.cli inspect
```

Sau khi cài WNTR, chạy mô phỏng PDD trong trạng thái bình thường.

```bash
python -m simulation.cli baseline
```

Kết quả JSON được tạo tại `simulation/outputs/baseline.json`.

Kiểm tra phương án đóng van và chạy phục hồi thủ công.

```bash
python -m simulation.cli topology
python -m simulation.cli recovery
```

Kết quả phục hồi được tạo tại `simulation/outputs/recovery.json`.

Tìm phương án tốt nhất bằng cách đánh giá toàn bộ tổ hợp có tối đa hai thao tác.

```bash
python -m optimization.cli exhaustive
```

Kết quả xếp hạng được tạo tại `optimization/outputs/exhaustive.json`.

Chạy Genetic Algorithm và so sánh với exhaustive search.

```bash
python -m optimization.cli ga
python -m optimization.cli compare
```

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

