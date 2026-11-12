# Optimization

Module này chứa baseline cô lập sự cố, hàm mục tiêu đa tiêu chí và các thuật toán tìm kiếm phương án phục hồi.

## Hàm mục tiêu

Mỗi phương án nhận điểm từ 0 đến 100 dựa trên năm thành phần đã chuẩn hóa.

- Khả năng đáp ứng nhu cầu nước: 40%.
- Tuân thủ ngưỡng áp suất: 20%.
- Khả năng kiểm soát thất thoát: 20%.
- Phạm vi nút bị ảnh hưởng: 15%.
- Số thao tác vận hành: 5%.

## Exhaustive search

Với 12 van và tối đa hai thao tác đóng van, hệ thống đánh giá 79 tổ hợp. Baseline là phương án đóng hai van ở hai đầu đường ống bị sự cố.

```bash
python -m optimization.cli exhaustive
```

Các trạng thái bình thường và sự cố được mô phỏng một lần rồi tái sử dụng. Mỗi ứng viên chỉ cần chạy thêm trạng thái phục hồi. Kết quả mặc định được ghi tại `optimization/outputs/exhaustive.json`.

