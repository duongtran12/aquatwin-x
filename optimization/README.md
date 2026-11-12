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

## Genetic Algorithm

Mỗi chromosome có 12 gene nhị phân tương ứng với 12 van. Gene bằng 1 biểu thị van được đóng. Thuật toán mặc định sử dụng quần thể 20 cá thể, chạy 20 thế hệ và giới hạn tối đa hai thao tác.

```bash
python -m optimization.cli ga
```

Các tham số có thể điều chỉnh trực tiếp từ dòng lệnh.

```bash
python -m optimization.cli ga --population-size 30 --generations 40 --mutation-rate 0.15 --seed 42
```

Thuật toán lưu cache theo chromosome, vì vậy một phương án lặp lại giữa các thế hệ chỉ được mô phỏng một lần. Kết quả và lịch sử fitness được ghi tại `optimization/outputs/ga.json`.

## So sánh thuật toán

Sau khi chạy exhaustive search và GA, tạo bảng đối chiếu bằng lệnh sau.

```bash
python -m optimization.cli compare
```

File `optimization/outputs/comparison.json` cho biết chênh lệch điểm, số phương án đã đánh giá, thời gian chạy và GA có tìm được nghiệm tối ưu toàn cục hay không.

