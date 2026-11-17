# Team

## Thông tin nhóm

- Tên nhóm: ChuCuoi
- Lớp: L3A
- Repo nhóm: `K5-L3A-DAY08-ChuCuoi-FromWorkflowsToAgents` (xem [SUBMISSION.md](SUBMISSION.md))
- URL repo, nhánh nộp, commit chốt: https://github.com/Ein05/K5-L3A-DAY08-ChuCuoi-FromWorkflowsToAgents, nhánh `main`, commit `0487e36` (trùng `report/team/decision_adr.md`)

## Thành viên

| STT | Họ tên | MSSV | Email | GitHub | Vai trò |
| --: | ------ | ---- | ----- | ------ | ------- |
|   1 | Nguyễn Đình Quang | 2A202603620 | quang8b9b@gmail.com | Quang-safjl | Shape A workflow + integration, báo cáo nhóm |
|   2 | Mai Huy Hoat | 2A202603656 | maihuyhoat@gmail.com | MHuyHoat | Shape B single agent |
|   3 | Lê Hải Bắc | 2A202603710 | lehbac05@gmail.com | Lehaibac05 | Shape C orchestrator + handoff, test trace an toàn |
|   4 | Vũ Đức Anh | 2A202603714 | 26ai.anhvd4@vinuni.edu.vn | Ein05 | Tổng hợp thông tin, viết report |

Gợi ý chia vai:

- Nhóm 6 người: integration; workflow; single agent; orchestrator; ledger/policy/crash; eval/report.
- Nhóm 4 người: workflow + integration; single; orchestrator + handoff; ledger + evaluation.

## Bảng đóng góp

`python -m lab8.check_submission` đọc bảng này bằng máy: giữ nguyên tiêu đề `## Bảng đóng góp` và các cột. Mỗi người một dòng: commit có nội dung và ít nhất một test đã thêm hoặc sửa.

| Người | Vai | Commit | Test đã thêm hoặc sửa |
| --- | --- | --- | --- |
| Nguyễn Đình Quang | Shape A workflow + integration, sửa budget shape B, ADR/research card/báo cáo nhóm | f49e55f, 0487e36 | `src/tests/test_workflow_shape.py` (20 test), `src/tests/test_single_budget.py` (2 test) |
| Mai Huy Hoat | Shape B single agent | 45307e6, 92b0ead | Không có test riêng trong commit cá nhân; các thay đổi được kiểm chứng bởi ma trận shape B (`src/tests/test_public_matrix.py`) và test budget được bổ sung sau khi merge (`src/tests/test_single_budget.py`) |
| Lehaibac05 | Shape C orchestrator + handoff | 4c6ca49, 94366fe | `src/tests/test_orchestrator_handoff.py`, `src/tests/test_trace_safety_all_shapes.py` |
| Vũ Đức Anh (Ein05) | Nhóm trưởng: tạo repo, điều phối và merge PR #1 | 865802a (merge), 0bba534 | Kiểm tra hồi quy các test được tích hợp trong PR #1: `src/tests/test_orchestrator_handoff.py`, `src/tests/test_trace_safety_all_shapes.py` |

## Cá nhân

Mỗi thành viên đồng thời tạo một báo cáo riêng trong `report/` theo dạng:

```text
report/team/<MSSV>_<HoTen>.md
```

Ví dụ: `report/team/20241234_NguyenVanAn.md`.

Mỗi thành viên đã có báo cáo riêng trong `report/team/` theo đúng quy tắc đặt tên.
