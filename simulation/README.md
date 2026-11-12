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

## Chạy kịch bản rò rỉ

Kịch bản mẫu tạo điểm rò ở giữa đường ống `P3`, bắt đầu tại giờ thứ 2 và kết thúc tại giờ thứ 12.

```bash
python -m simulation.cli failure
```

Chạy một file kịch bản khác.

```bash
python -m simulation.cli failure --scenario simulation/scenarios/my_leak.json
```

Kết quả `simulation/outputs/failure.json` gồm mức phục vụ, số nút vi phạm áp suất, số nút bị ảnh hưởng, lưu lượng rò và tổng thể tích thất thoát.

