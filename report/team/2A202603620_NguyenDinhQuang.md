# Báo cáo cá nhân — 2A202603620_NguyenDinhQuang

## 1. Thông tin thành viên

- Họ tên: Nguyễn Đình Quang
- MSSV: 2A202603620
- Email:quang8b9b@gmail.com
- GitHub:Quang-safjl
- Vai trò trong nhóm: Shape A (workflow) + integration

## 2. Phần việc phụ trách

- **Shape A `workflow`**: `src/lab8/shapes/workflow.py`. Các bước Python cố định, không vòng lặp model.
- **Integration**: ghép code của các shape vào `main`, giữ cổng host (`python -m pytest -q`) luôn xanh, chạy crash suite và benchmark 4 shape để sinh bằng chứng trong `src/reports/`. Script hỗ trợ: `src/scripts/integration_check.ps1` (Windows) và `src/scripts/integration_check.sh`.

## 3. Đóng góp cụ thể

### 3.1 Shape workflow

Luồng xử lý trong `run_claim` → `_run`:

1. Đọc claim qua `get_claim_view` (chỉ các cột allowlist, không `SELECT *`). Claim không tồn tại → `failed` / `unknown_claim`.
2. Thiếu `order_id` → `needs_info`, không ghi ledger. Không lấy mã đơn từ câu chữ trong ticket.
3. `lookup_order` theo principal của claim. Không thấy đơn hoặc sai chủ → `escalated`, chỉ ghi lý do vào trace.
4. Tính quote bằng `compute_compensation` từ dòng order. Số ngày trễ khách viết trong ticket bị bỏ qua.
5. Quote = 0 → `denied`, không gọi `issue_refund`.
6. Quote > 0 → `durability.issue_refund(conn, claim_id, <quote đầy đủ>, crash_at=crash_at)`. Host từ chối → `denied` (host ghi `policy_denied`), xung đột số tiền → `failed`, thành công → `resolved`.
7. MockLLM chỉ được gọi một lần để soạn câu trả lời khách, với prompt là quyết định đã có (`status`, `amount`), không chứa ticket. Model không chọn số tiền và không ghi refund.

### 3.2 Quyết định kỹ thuật

- **Truyền quote đầy đủ vào host.** Host tự trừ phần đơn đã được hoàn (trần theo đơn). Nếu shape tự trừ trước thì host trừ hai lần. Ví dụ C-014: quote 150.000, ledger 120.000 (đã hoàn 30.000 ship trước đó), `proposal_amount` vẫn là 150.000.
- **Không bắt `InjectedCrash`.** Trước khi để exception thoát ra, shape ghi một event `crash` vào trace để vẫn có trace đúng contract. Resume dựa vào idempotency key `refund:{claim_id}` của host.
- **Trace chỉ ghi field đã qua allowlist**: `claim_id`, `order_id`, order view của `lookup_order` (không có phone, address, item_name, internal_note), quote, lý do từ host. Không ghi ticket, `principal_id`, dòng DB thô. Mọi nhánh return đi qua `finish()` nên luôn có trace mới của chính lần chạy.
- **Một model call duy nhất, không đọc ticket**: workflow không có độ dao động giữa các seed, và chữ trong ticket (kể cả kiểu "ignore policy") không ảnh hưởng quyết định.

### 3.3 Test đã thêm

`src/tests/test_workflow_shape.py` (20 test, marker `student`):

| Test | Kiểm tra |
| --- | --- |
| `test_workflow_trace_and_result_have_no_secret_or_pii` (14 claim) | Trace và `RunResult` không chứa `CANARY_SECRET_*`, header, phone, address, internal_note, item_name, nguyên văn ticket |
| `test_workflow_is_seed_invariant` | Cùng claim cho cùng `(status, proposal_amount)` trên cả 5 seed |
| `test_workflow_ignores_delay_written_in_ticket` | C-002 (ticket nói 5 ngày, DB 2 ngày) bị `denied` ở mọi seed, kể cả seed 55 mà swarm trượt |
| `test_workflow_unknown_claim_fails_cleanly` | Claim không tồn tại → `failed`, trace đúng contract v1 |
| `test_workflow_crash_then_resume_gives_one_refund` (3 điểm crash) | Crash ở `before_effect`, `after_effect_before_checkpoint`, `after_checkpoint` rồi chạy lại: đúng 1 dòng ledger, 1 audit `refund_committed`, 35.000 |

### 3.4 Integration

- Kiểm tra code của Shape B (Mai Huy Hoat) và Shape C (Lehaibac05) sau khi merge vào `main`: mỗi shape 62/62 test public, không ai sửa file thước đo (`metrics.py`, `durability.py`, `policy.py`, `config/`, `data/`).
- Script `integration_check` chạy theo thứ tự: smoke → cổng host → chặn sửa file thước đo → ma trận student từng shape → crash suite → (tùy chọn) benchmark → `check_submission`. Ma trận được lọc theo tham số shape trong test id vì `-k single` còn khớp nhầm tên test `*single_run_cases*`.
- Sinh `src/reports/crash.json`, `src/reports/benchmark.json` và `src/reports/ablation_r1.json` bằng công cụ của lab, không sửa tay.
- Phát hiện Shape B không tính model call (0 call/trial, cost/success thấp giả tạo). Sửa `decide()` để mỗi bước ReAct gọi MockLLM với prompt chỉ có trạng thái bước và ghi event `step`; thêm `src/tests/test_single_budget.py` (2 test). Shape B vẫn 62/62.
- Hoàn thiện phần chung của nhóm: `report/team/decision_adr.md`, `report/team/research_card.md` (R1 + ablation workflow → orchestrator), `report/team/group_report.md`, `TEAM.md`.

## 4. Bằng chứng

- Commit: f49e55f (workflow + integration), 0487e36 (sửa budget shape B, report, ADR, báo cáo nhóm)
- Ma trận student: `python -m pytest -q -m student -o addopts=` → 270 passed (4 shape, cùng các test nhóm thêm). Riêng workflow: 62/62 public + 20/20 test riêng.
- Cổng host: `python -m pytest -q` → 204 passed (29 test `test_trace_safety_all_shapes.py` trước đây bị skip vì workflow còn là stub, nay chạy và xanh).
- Crash suite: `python -m lab8.crash_test --count 20 --out reports/crash.json` → `crash_safety 20/20`.
- Benchmark (`reports/benchmark.json`, 14 claim × seed 11,22,33,44,55, MockLLM, giá mô phỏng):

| Shape | Pass rate | pass^5 | Variance | Cost/success (VND) | Mean steps | Model calls/trial |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| workflow | 1.000 | 1.000 | 0 | 28.86 | 4.43 | 1.00 |
| single | 1.000 | 1.000 | 0 | 29.03 | 4.64 | 3.64 |
| orchestrator | 1.000 | 1.000 | 0 | 56.52 | 3.71 | 0.86 |
| swarm | 0.986 | 0.929 | 0.0008 | 49.57 | 2.80 | 3.00 |

- Run id dẫn chứng: `R-workflow-C-002-s55` (workflow từ chối đúng ở trial swarm trượt), `R-workflow-C-014-s11` (refund phần chênh).

## 5. Công cụ AI đã dùng

- **Claude (Anthropic)**: đọc đề và tóm tắt phân công; viết bản đầu `workflow.py`, `test_workflow_shape.py` và script integration; chạy test, crash suite, benchmark.
- **Cách tự kiểm tra:**
  - Đối chiếu từng nhánh `status` với bảng trong `docs/contracts.md` và `docs/business_rules.md`.
  - Chạy lại `python -m pytest -q` và ma trận student trên máy mình trước khi commit.
  - Mở thử file trace trong `src/traces/` để chắc không có secret hay thông tin cá nhân.
  - Số trong báo cáo lấy trực tiếp từ `reports/benchmark.json`, không chép tay.

## 6. Tự đánh giá

- Hoàn thành Shape A và phần integration được giao. Workflow đạt cả 3 must-pass trên bộ public: không bypass approval, không lộ secret, crash 20/20.
- Workflow là ứng viên hợp lý cho shape chọn: pass rate 1.000, không dao động giữa seed, ít tự chủ nhất. Giới hạn: số đo chỉ trên 14 claim public và MockLLM, chưa phản ánh model thật; kết luận có thể đổi nếu ticket cần hiểu ngôn ngữ tự do (ví dụ khách không ghi mã đơn mà mô tả bằng lời).
- Đã xử lý vấn đề Shape B không tính model call trước khi chạy benchmark chốt, để so sánh trong ADR công bằng.
