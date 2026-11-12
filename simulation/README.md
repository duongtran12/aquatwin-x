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

## Thử phương án phục hồi thủ công

Mạng demo sử dụng một lớp dữ liệu riêng để mô tả vị trí van cô lập tại hai đầu mỗi đường ống. Kịch bản mẫu đóng hai van ở hai đầu `P3` để cô lập điểm rò, trong khi các đường ống còn lại duy trì tuyến cấp thay thế tới `J3`.

Kiểm tra kết nối tới nguồn trước khi chạy mô phỏng thủy lực.

```bash
python -m simulation.cli topology
```

Chạy ba trạng thái bình thường, xảy ra rò rỉ và phục hồi thủ công.

```bash
python -m simulation.cli recovery
```

Kết quả được ghi tại `simulation/outputs/recovery.json`, gồm danh sách thao tác thực tế, KPI trước và sau phục hồi cùng mức cải thiện.

