# Báo cáo cá nhân — Shape B (Single Agent)

## 1. Thông tin thành viên

| Trường | Giá trị |
|---|---|
| Họ và tên | Mai Huy Hoat |
| MSSV | 2A202603656 |
| Email | maihuyhoat@gmail.com|
| GitHub | [https://github.com/MHuyHoat] |
| Vai trò trong nhóm | Thành viên — phụ trách Shape B (Single Agent) |

## 2. Phần việc phụ trách

- **File chính:** `src/lab8/shapes/single.py`
- **Mô tả ngắn:** Xây dựng kiến trúc **Single Agent** cho bài toán xử lý claim hoàn phí vận chuyển của LogiX-VN. Shape B dùng một vòng lặp **ReAct tối đa 8 bước**; `decide()` chỉ được chọn các tool **đọc** (`get_claim_view`, `lookup_order`, `lookup_policy`, `lookup_refund_history`, `compute_compensation`); sau khi vòng lặp kết thúc, **code của shape** mới là bên gọi `durability.issue_refund` để ghi refund vào ledger. Ranh giới rõ ràng: **model chỉ đọc + đề xuất quote, code shape kiểm soát việc ghi tiền**.

## 3. Đóng góp cụ thể

### 3.1 Code

- Implement `run_claim` và `_run` trong `src/lab8/shapes/single.py`.
- Tạo `Budget()`, `Trace(make_run_id("single", claim_id, seed))`.
- Truy vấn claim từ bảng `claims`; xử lý các nhánh:
  - Claim không tồn tại → `status="failed"`, `error_reason="unknown_claim"`.
  - Claim thiếu `order_id` → `status="needs_info"`, `error_reason="missing_order_id"` (không lấy mã đơn từ câu chữ trong ticket).
- Viết hàm `decide(seen)` cho vòng ReAct: chỉ chọn tool đọc, dừng đúng lúc bằng `{"final": {...}}`.
- Gọi `run_react(..., max_steps=8, worker=True)` để **chặn write tool từ `decide`** (`worker=True` khiến `dispatch` ném `ToolRejected` nếu cố gọi `issue_refund`).
- Sau vòng lặp: lấy **full quote** từ `compute_compensation`, rồi gọi `issue_refund(conn, claim_id, proposal, crash_at=crash_at)`.
- Ở CP3: bắt `InjectedCrash`, ghi trace `crash`, rồi **re-raise** để crash thoát ra ngoài (không nuốt exception).
- Mọi nhánh return đều đi qua `finish(...)` để trace và ledger nhất quán.

### 3.2 Quyết định kỹ thuật

1. **Truyền full quote (không phải net amount) vào `issue_refund`.** Với claim C-014, quote đầy đủ là **150.000 VND**; host tự trừ **30.000 VND** đã hoàn trước đó, nên ledger chỉ ghi **120.000 VND**. Nếu truyền net vào `issue_refund`, host từ chối → `status="failed"`.
2. **Dùng `worker=True` trong `run_react`.** Đây là hàng rào an toàn: model không thể tự ghi tiền; chỉ code shape mới được gọi `issue_refund`.
3. **Không tin ticket, chỉ tin order row.** Trường `delay_days` phải lấy từ `lookup_order`, không đọc từ câu chữ khách hàng.
4. **Trace trên mọi nhánh return**, kể cả nhánh lỗi sớm (`unknown_claim`, `missing_order_id`, `step_cap`), để grader thấy được lý do.

### 3.3 Test đã pass

```bash
cd src
python -m pytest tests/test_public_matrix.py -o addopts= -k "single]" -v
```
### 4. Bằng chứng

Link commit: https://github.com/Ein05/K5-L3A-DAY08-ChuCuoi-FromWorkflowsToAgents/tree/45307e68233fbe66f9efeb4e3ea787149f537028
...

## 5. Công cụ AI đã dùng

Công cụ: DeepSeek Chat .

...

## 6. Tự đánh giá
Hoàn thành công việc được giao của nhóm