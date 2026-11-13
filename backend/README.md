# AquaTwin-X Backend

Backend cung cấp API cho network catalog, mô phỏng thủy lực, thử phương án thủ công và tối ưu phục hồi.

## Khởi động

Chạy từ thư mục gốc của repository.

```bash
uvicorn backend.app.main:app --reload
```

Swagger UI được cung cấp tại `http://localhost:8000/docs`.

## API chính

- `GET /api/networks`
- `GET /api/networks/{network_id}`
- `POST /api/simulations/baseline`
- `POST /api/simulations/failure`
- `POST /api/simulations/what-if`
- `POST /api/recovery/optimize`
- `GET /api/jobs/{job_id}`
- `GET /api/results/{job_id}`

Optimization chạy bằng một worker riêng và trạng thái job được lưu trong bộ nhớ của tiến trình backend. Khi backend khởi động lại, các job cũ không còn tồn tại.
