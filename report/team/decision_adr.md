# Decision record

Điền sau dấu `:` trên cùng dòng, không xóa nhãn. Giảng viên và `python -m lab8.check_submission` (chạy trong `src/`) đọc các dòng này bằng máy. Không đổi tên hay dời file này khỏi `report/team/`.
`Shape chọn` phải là đúng một trong: `workflow`, `single`, `orchestrator`, `swarm`. Đây là shape được chấm cổng hidden.

- Shape chọn: workflow
- Commit hash: 0487e36
- Run id dẫn chứng: R-workflow-C-002-s55 (từ chối đúng ở trial swarm trượt), R-workflow-C-014-s11 (hoàn phần chênh 120.000), R-swarm-C-002-s55 (swarm fail) — src/reports/benchmark.json
- Pass rate / pass^5 / seed min-max / variance: 1.000 / 1.000 / 1.000–1.000 / 0.000000 (14 claim public × seed 11,22,33,44,55 = 70 trial, src/reports/benchmark.json)
- Cost per success (mô phỏng, VND): 28.86 (single 29.03, swarm 49.57, orchestrator 56.52; giá mô phỏng config/pricing.yaml, không phải hóa đơn API)
- Crash safety: 20/20 (src/reports/crash.json)
- Secret leak / approval bypass: 0 / 0 trên bộ public (test_workflow_shape.py quét trace + RunResult cho 14 claim; test_trace_safety_all_shapes.py; T07 approval hỏng và T13 đơn đã hoàn đủ bị host chặn kèm policy_denied, T08 bị cap theo approval 20.000, T09 "ignore policy" bị từ chối)

Ví dụ một dòng đã điền: `- Shape chọn: workflow`, `- Crash safety: 20/20 (src/reports/crash.json)`.

## Vì sao shape này

Trên cùng corpus (14 claim public), cùng 5 seed, cùng bảng giá và cùng MockLLM, ba shape nhóm viết đều đạt pass rate 1.000 và pass^5 1.000, còn swarm đạt 0.986 / 0.929 vì tin số ngày trễ trong ticket ở C-002 seed 55. Khi pass rate bằng nhau, đề yêu cầu chọn shape **ít tự chủ nhất mà vẫn làm được việc**: workflow có luồng cố định, model chỉ soạn câu trả lời sau khi quyết định đã xong, không đọc ticket, nên variance giữa seed bằng 0 theo cấu tạo chứ không phải do may. Chi phí mô phỏng thấp nhất (28.86 VND/success, 1 model call và ~2.8 tool call mỗi trial), ngang single (29.03) và bằng khoảng một nửa orchestrator (56.52). Mỗi quyết định có thể đọc lại từ trace theo đúng thứ tự claim → order → quote → host → decision, dễ audit hơn một vòng ReAct.

## Có đáng đổi lấy multi-agent không

Không, với dữ liệu hiện có. Orchestrator không tăng pass rate (1.000 → 1.000) nhưng gần gấp đôi cost/success (28.86 → 56.52) vì thêm handoff và investigator đọc lại cùng dữ liệu. Swarm vừa đắt hơn (49.57) vừa kém hơn (0.986, variance 0.0008). Bài toán claim là một chuỗi tuần tự (claim → đơn → policy → quote → ghi), không có nhánh song song để chia việc, nên thêm agent chỉ thêm chi phí phối hợp. Quyết định sẽ đảo lại nếu: (1) bộ hidden có nhiều ticket thiếu dữ liệu có cấu trúc (không có `order_id`, khách mô tả đơn bằng lời) mà chỉ model mới tìm được; (2) mỗi claim cần tra nhiều nguồn độc lập (nhiều carrier, nhiều đơn) có thể chạy song song; (3) có model thật mà một agent thêm kiểm chứng làm pass rate tăng rõ hơn phần cost tăng. Khi đó single hoặc orchestrator cần được đo lại trên cùng corpus trước khi đổi.

## Trace và bằng chứng

Trace của workflow (`src/traces/<run_id>.json`, contract v1) ghi các event: `claim` (claim_id, found, order_id), `order` (order view đã qua allowlist của `lookup_order`: order_id, status, delay_days, shipping_fee_vnd, paid_vnd, damage_verified, carrier), `quote` (amount_vnd, reason, clause_ids, parts), `host` (ok, reason, conflict), `decision` (status, proposal_amount, reason) và `crash` (điểm crash) khi có. Cố ý **không** ghi: nguyên văn ticket (dữ liệu người dùng, có thể chứa lệnh giả hoặc thông tin cá nhân), `principal_id`, `parent_secret`, `raw_headers`, phone, address, item_name, internal_note và mọi dòng DB thô. Shape không in gì ra stdout và không ghi file nào khác ngoài trace. Nếu trace nằm ngoài chỗ scanner quét được thì không chứng minh được hệ thống sạch, nên nhóm giữ mọi log trong file trace mà grader quét, và thêm test quét trace của cả 14 claim public tìm mọi secret và giá trị PII có trong world (`src/tests/test_workflow_shape.py`, `src/tests/test_trace_safety_all_shapes.py`).

## Giới hạn

MockLLM không phải model sản xuất: chi phí là token mô phỏng theo `config/pricing.yaml`, latency để `unavailable`. Số đo chỉ trên 14 claim public; bộ hidden 40 claim × 5 seed do giảng viên chấm. Không sửa JSON trong `src/reports/` cho đủ ngưỡng; mọi số ở trên lấy từ file do `lab8.benchmark` và `lab8.crash_test` sinh ra.
