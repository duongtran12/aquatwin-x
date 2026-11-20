# Kịch bản demo AquaTwin-X

## Chuẩn bị trước buổi bảo vệ

```powershell
docker compose up --build
Invoke-RestMethod http://localhost:8000/api/health/runtime
```

Chỉ bắt đầu lấy số liệu khi response có `effective_mode = real`, `wntr_available = true` và `synthetic_data = false`.

Mở dashboard tại `http://localhost:5173` và Swagger tại `http://localhost:8000/docs`.

## Luồng demo 8–10 phút

1. **Giới thiệu topology:** chọn mạng `aquatwin_demo`, giải thích node, pipe và valve.
2. **Tạo sự cố:** chọn pipe `P3`, preset `Major leak`, chạy Failure Simulation.
3. **Phân tích ảnh hưởng:** trình bày service availability, pressure violations, affected nodes và leakage volume.
4. **What-if thủ công:** chọn một hoặc hai valve gần P3, chạy Manual Isolation và xem thay đổi KPI.
5. **Tối ưu AI:** giữ seed cố định, cấu hình population/generations, chạy Genetic Optimization.
6. **Giải thích kết quả:** trình bày best score, convergence chart và danh sách thao tác van.
7. **Evidence:** mở History, xem detail, so sánh hai run và mở printable report.
8. **Thực nghiệm:** mở Experiments/Analytics hoặc GitHub Actions artifact để chứng minh kết quả Real WNTR.

## Ảnh nên chụp cho báo cáo

| STT | Nội dung ảnh | Vị trí |
| ---: | --- | --- |
| 1 | Dashboard và topology mạng | Overview |
| 2 | Thiết lập kịch bản rò rỉ | Scenario Builder |
| 3 | KPI sau sự cố | Impact Analysis |
| 4 | Thử nghiệm đóng van thủ công | What-if Control |
| 5 | Cấu hình và kết quả GA | AI Recovery |
| 6 | Đồ thị hội tụ GA | Convergence |
| 7 | So sánh hai run | History Comparison |
| 8 | Báo cáo evidence có thể in | Open Report |
| 9 | Benchmark summary | GitHub Actions Summary |
| 10 | Runtime Real WNTR | `/api/health/runtime` |

## Khi máy demo không chạy được WNTR

- Không tắt Windows Application Control.
- Khởi động Docker Desktop và chờ Linux Engine sẵn sàng.
- Chạy lại `docker compose up --build`.
- Nếu chỉ cần trình diễn giao diện, dùng `AQUATWIN_RUNTIME_MODE=demo` và nói rõ số liệu tổng hợp không dùng trong kết luận.
- Evidence chính thức vẫn lấy từ GitHub Actions Full Benchmark đã chạy trên Linux với Real WNTR.

Kết thúc bằng `docker compose down`.
