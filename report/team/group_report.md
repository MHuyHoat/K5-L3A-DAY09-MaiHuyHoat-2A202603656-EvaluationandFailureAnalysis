# Báo cáo nhóm — Lab 8 LogiX-VN

Tối đa 5 trang ngoài phụ lục. Số liệu lấy từ file trong `src/reports/`, không chép tay từ terminal.

## 1. Thông tin nhóm

- Tên nhóm: ChuCuoi (lớp L3A)
- Thành viên: xem `TEAM.md`
- Commit chốt (trùng `report/team/decision_adr.md`): `0487e36`

## 2. Mục tiêu và cách tiếp cận

Bài toán: xử lý claim hoàn phí vận chuyển của LogiX-VN (dữ liệu giả) bằng bốn kiến trúc cùng chữ ký `run_claim`, rồi chọn kiến trúc ít tự chủ nhất mà vẫn đạt, bằng số đo chứ không bằng cảm giác "multi-agent tốt hơn". Nhóm hiểu ranh giới cốt lõi là: số tiền, approval, trần theo đơn và chống ghi trùng do **code và host** quyết; model chỉ đọc và soạn chữ; chữ trong ticket là dữ liệu người dùng, không phải lệnh.

Chia việc theo gợi ý nhóm 4 người: workflow + integration (Quang), single (Hoat), orchestrator + handoff (Lehaibac05), nhóm trưởng tạo repo và merge (Ein05). Thứ tự: đọc contract và `swarm_reference.py` (CP1) → mỗi người làm shape của mình trên branch riêng (CP2–CP3) → merge từng PR, chạy lại cổng host và ma trận student sau mỗi lần merge → crash suite và benchmark trên commit đã merge đủ ba shape (CP4–CP5) → ADR, research card, báo cáo.

## 3. Giải pháp

Cả ba shape dùng chung một khuôn: đọc claim qua `get_claim_view` (không `SELECT *`), không lấy mã đơn từ ticket, tra đơn qua `lookup_order` theo `principal_id` của claim, tính tiền bằng `compute_compensation` từ dòng order, rồi truyền **quote đầy đủ** vào `durability.issue_refund` cùng `crash_at`, không bắt `InjectedCrash`. Mọi nhánh return đi qua `common.finish()` nên luôn có trace contract v1 mới và `refund_effects` lấy từ ledger.

| Shape | Đọc gì | Ai quyết định | Model làm gì | Gọi host |
| --- | --- | --- | --- | --- |
| A workflow | claim view → order → quote | Các bước Python cố định | 1 call soạn câu trả lời, prompt chỉ có status/amount, không có ticket | Code shape gọi `issue_refund` |
| B single | ReAct tối đa 8 bước, `run_react(..., worker=True)` | `decide()` chỉ được chọn tool đọc (`worker=True` chặn tool ghi) | 1 call "react" mỗi bước, prompt chỉ có tên tool và trạng thái | Code shape gọi sau vòng lặp |
| C orchestrator | Orchestrator đọc claim view; investigator chạy tool đọc qua `run_readonly_investigators` | Orchestrator | Soạn câu trả lời | Orchestrator gọi `issue_refund` |
| D swarm (có sẵn) | Peer + investigator | Peer, có `REFERENCE_WEAKNESS` | 3 call/trial | Swarm gọi |

**Handoff (shape C):** dựng bằng `lab8.handoff.make_handoff` với `facts={}` và chỉ tool đọc (`make_handoff` từ chối tool ghi); ticket, `parent_secret`, `raw_headers` ở lại parent. Trace ghi bản handoff đã sanitize và một tóm tắt investigator (order_visible, order_reason, already_refunded_vnd), không ghi order row thô.

**Trace:** workflow ghi `claim`, `order` (view allowlist), `quote`, `host`, `decision`, `crash`; single ghi thêm `step` cho mỗi bước ReAct. Không shape nào ghi ticket, `principal_id`, secret, header, phone, address, item_name, internal_note hay in ra stdout. Tóm tắt bằng LLM không được coi là redaction: nhóm loại field ngay từ allowlist chứ không nhờ model che.

## 4. Kết quả

Bộ public: 14 claim × seed 11, 22, 33, 44, 55 = 70 trial mỗi shape, MockLLM, giá mô phỏng `config/pricing.yaml`, SQLite mới cho mỗi trial (`src/reports/benchmark.json`).

| Shape | Pass rate | pass^5 | Seed min–max | Variance | Cost/success (VND) | Mean / p95 steps | Model calls / trial | Tool calls / trial |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| workflow | 1.000 | 1.000 | 1.000–1.000 | 0 | 28.86 | 4.43 / 5 | 1.00 | 2.79 |
| single | 1.000 | 1.000 | 1.000–1.000 | 0 | 29.03 | 4.64 / 5 | 3.64 | 2.71 |
| orchestrator | 1.000 | 1.000 | 1.000–1.000 | 0 | 56.52 | 3.71 / 4 | 0.86 | 5.57 |
| swarm | 0.986 | 0.929 | 0.929–1.000 | 0.0008 | 49.57 | 2.80 / 3 | 3.00 | 4.66 |

- Lỗi duy nhất: `R-swarm-C-002-s55`, swarm trả `resolved` thay vì `denied` vì ở seed chia hết cho 5 nó tin "trễ 5 ngày" trong ticket thay vì `delay_days = 2` của đơn. Ba shape nhóm viết đều từ chối đúng claim này ở mọi seed.
- Crash safety: `20/20` (`src/reports/crash.json`). Test riêng cho workflow crash ở cả 3 điểm rồi chạy lại vẫn ra 1 dòng ledger và 1 audit `refund_committed`.
- Test: `python -m pytest -q` (cổng host) 204 passed; `python -m pytest -q -m student -o addopts=` 270 passed, 0 failed.
- Ablation R1 (workflow → orchestrator, `src/reports/ablation_r1.json`): pass không đổi, cost/success ×1.96. Chi tiết trong research card.
- Chưa tự kiểm trên `student_drop/` vì nhóm không có bộ này trên máy; bộ hidden 40 claim × 5 seed do giảng viên chấm.

Quyết định kiến trúc: **workflow** — xem `report/team/decision_adr.md`. Phiếu nghiên cứu và ablation: xem `report/team/research_card.md`.

## 5. Khó khăn và cách xử lý

1. **Shape single không tính model call.** Benchmark lần đầu cho single 0 model call và 1 step mỗi trial: `decide()` là luật Python cố định, không gọi MockLLM, nên cost/success của single (27.14) thấp hơn workflow một cách không công bằng, trái với yêu cầu "Count model calls in the Budget so cost stays comparable" trong docstring. Cách xử lý: mỗi bước ReAct gọi `mock_llm.complete(purpose="react")` với prompt chỉ chứa trạng thái bước (không ticket) và ghi event `step`; thêm `src/tests/test_single_budget.py`. Sau khi sửa: 3.64 model call/trial, cost/success 29.03, vẫn 62/62 test public.
2. **`pytest -k single` chọn nhầm test.** Lệnh tự kiểm trong CHECKPOINTS `-k single` còn khớp tên test `test_public_single_run_cases` của mọi shape, ra "60 failed, 182 passed" dù single đã đúng. Script `src/scripts/integration_check.ps1` / `.sh` lọc theo tham số shape trong test id (`[...-single]`) nên mỗi shape ra đúng 62 test.
3. **Test trace an toàn bị skip.** `test_trace_safety_all_shapes.py` (29 test) skip khi workflow còn là stub, nên cổng host xanh nhưng chưa kiểm hết. Sau khi merge workflow, cả 29 test chạy và xanh.
4. **Quyền push.** Một thành viên ban đầu không push được lên repo của nhóm trưởng; xử lý bằng cách làm việc trên branch riêng và mở Pull Request để nhóm trưởng merge.

## 6. Tổng hợp đóng góp

Chi tiết đóng góp của từng thành viên nằm trong `TEAM.md` (bảng đóng góp) và các báo cáo cá nhân `report/team/<MSSV>_<HoTen>.md`.

## 7. Hạn chế và hướng cải thiện

- MockLLM không phải model sản xuất; latency là `unavailable`; chi phí là token mô phỏng. MockLLM không hiểu sai ngôn ngữ như model thật, nên lợi ích kiểm chứng của agent (nếu có) không xuất hiện trong số đo.
- Corpus public chỉ 14 claim và không có claim nào cần tra nhiều nguồn song song, nên kết luận "multi-agent không đáng" chỉ đúng cho task tuần tự này.
- Workflow sẽ yếu nếu hidden có ticket thiếu `order_id` mà mã đơn chỉ nằm trong lời kể của khách: workflow trả `needs_info` theo luật, đúng luật nhưng có thể làm khách phải hỏi lại. Kết luận sẽ đổi nếu claim cần hiểu ngôn ngữ tự do hoặc cần tra song song nhiều đơn/carrier; khi đó cần đo lại single và orchestrator trên cùng corpus.
- Cải thiện: thêm test hidden tự tạo (approval hết hạn đúng ngày `as_of`, đơn hoàn nhiều lần, ticket có chèn lệnh) và đo lại trên `student_drop/` khi có.

## 8. Tài liệu tham khảo

- Đề bài và contract: `README.md`, `docs/business_rules.md`, `docs/contracts.md`, `docs/metrics.md`.
- Kim et al., *Towards a Science of Scaling Agent Systems*, Google Research / Google DeepMind / MIT, arXiv 2512.08296, https://arxiv.org/abs/2512.08296.
- Google Research Blog, *Towards a science of scaling agent systems: When and why agent systems work*, 28/01/2026, https://research.google/blog/towards-a-science-of-scaling-agent-systems-when-and-why-agent-systems-work/.
