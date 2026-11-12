# Simulation

Module Digital Twin chịu trách nhiệm đọc mạng EPANET, tạo kịch bản sự cố, thực thi WNTR và chuẩn hóa kết quả mô phỏng.

## Kiểm tra file mạng

Chạy từ thư mục gốc của dự án.

```bash
python -m simulation.cli inspect
```

Kết quả được ghi mặc định vào `simulation/outputs/baseline.json`.

## Chạy trạng thái bình thường

```bash
python -m simulation.cli baseline
```

Có thể chọn file mạng và đường dẫn kết quả khác.

```bash
python -m simulation.cli baseline --network path/to/network.inp --output path/to/result.json
```

Mạng `aquatwin_demo.inp` gồm một nguồn, bốn nút nhu cầu và sáu đường ống tạo thành mạng vòng. Cấu trúc này được dùng để kiểm tra tuyến cấp thay thế trong các giai đoạn phục hồi tiếp theo.

