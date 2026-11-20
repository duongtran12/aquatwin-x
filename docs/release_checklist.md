# Checklist nghiệm thu AquaTwin-X v1.0.0

## Chức năng

- [x] Đọc và trực quan hóa EPANET INP.
- [x] Mô phỏng baseline và pipe leak.
- [x] Đánh giá đóng/mở van thủ công.
- [x] Tối ưu recovery bằng Genetic Algorithm.
- [x] Theo dõi, hủy job và cấu hình GA trên dashboard.
- [x] Batch experiment và benchmark với exhaustive search.
- [x] History SQLite, filter, archive/restore và so sánh run.
- [x] Xuất JSON, CSV, ZIP và printable report.
- [x] Import custom network và surveyed valve registry.

## Chất lượng

- [x] Backend unit, API và end-to-end acceptance tests.
- [x] Frontend API/logic tests và production build.
- [x] CI chạy Real WNTR smoke test trên Linux.
- [x] Full benchmark tạo evidence artifact 90 ngày.
- [x] Runtime Demo/Real được phân biệt rõ.
- [x] Upload có giới hạn dung lượng và validation.
- [x] CORS cấu hình bằng environment và có security headers.

## Trước khi nộp

- [x] Chạy `python -m pytest -q` trên commit cuối: 67 tests passed.
- [x] Chạy `npm test` và `npm run build` trong `frontend`: 19 tests passed, build thành công.
- [ ] Xác nhận GitHub Actions xanh.
- [ ] Chụp ảnh theo [demo_guide.md](demo_guide.md).
- [ ] Tải và lưu artifact benchmark cùng báo cáo.
- [ ] Tạo tag `v1.0.0` sau khi commit cuối đã lên `main`.
