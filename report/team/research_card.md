# Research card

File này nằm cố định ở `report/team/research_card.md`; `python -m lab8.check_submission` đọc cột "Nhóm điền" bằng máy.

Phần này nối tiếp phần mini research ở buổi lý thuyết (slide 62–63). Chọn **một** câu R1–R4, điền 6 dòng, rồi biến nó thành **một ablation** chạy được trong lab: giữ nguyên model (MockLLM), tool, seed, corpus và giá, chỉ thay đổi một biến.

| Câu | Nguồn (thư viện tham khảo, slide 68–69) | Câu hỏi gợi ý cho lab |
| --- | --- | --- |
| R1 · Scaling | Google Research 2026, *Towards a Science of Scaling Agent Systems* | Task claims chủ yếu tuần tự hay song song được? Dự đoán thêm investigator sẽ làm pass rate và cost/success thay đổi thế nào. |
| R2 · Failure taxonomy | MAST, NeurIPS 2025, *Why Do Multi-Agent LLM Systems Fail?* | Các trial fail của swarm (seed 55) thuộc nhóm nào: lỗi giao việc, lệch mục tiêu, hay lỗi kiểm chứng? |
| R3 · Architecture choices | AgentArch, AACL 2026 | Nếu đổi topology mà giữ nguyên mọi thứ khác, biến nào phải cố định để kết luận còn đúng? |
| R4 · Evaluation confounders | EMNLP 2026, *Rethinking Evaluation of MAS Efficiency* | Làm sao chứng minh chênh lệch giữa A/B/C/D là do topology, không phải do prompt, tool hay seed? |

## Phiếu của nhóm

Điền vào cột cuối. Không xóa hai cột đầu.

| Field | Hướng dẫn | Nhóm điền |
| --- | --- | --- |
| CÂU | R1 / R2 / R3 / R4 | R1 · Scaling |
| SOURCE | Paper/blog, năm, URL, loại bằng chứng (benchmark, production report, blog kinh nghiệm) | Kim et al. (Google Research, Google DeepMind, MIT), *Towards a Science of Scaling Agent Systems*, arXiv 2512.08296 (12/2025) và blog Google Research 28/01/2026, https://arxiv.org/abs/2512.08296 — loại bằng chứng: benchmark có kiểm soát (180 cấu hình, 5 kiến trúc, 3 họ LLM) |
| CLAIM | Một kết luận gốc của nguồn. Không viết rộng hơn phạm vi paper | Phối hợp nhiều agent cải thiện mạnh trên task song song hóa được nhưng làm giảm hiệu quả trên task tuần tự; thêm agent thường chạm trần chứ không tăng mãi |
| BOUNDARY | Model / dataset / setup giới hạn kết luận đó | Model thật (OpenAI, Google, Anthropic), 4–6 benchmark agentic của paper, ngân sách token được cân bằng; không có MockLLM, không có ledger tiền hay host gate như LogiX-VN, không đo task claim nghiệp vụ |
| HYPOTHESIS | Nếu đổi shape A→B (hoặc bật/tắt một thành phần), metric X sẽ đổi theo hướng nào, khoảng bao nhiêu | Claim LogiX-VN là chuỗi tuần tự (claim → đơn → policy → quote → ghi). Đổi A workflow → C orchestrator (thêm 1 investigator): pass rate không tăng (giữ 1.000, chênh ≤ 0), cost/success tăng khoảng 1.5–2.5 lần vì thêm handoff và tool call lặp |
| METHOD | Biến giữ cố định: model, tools, seed, corpus, giá, evaluator. Biến duy nhất được thay đổi: … | Giữ cố định: MockLLM, bộ tool đọc, host `durability.issue_refund`, seed 11,22,33,44,55, corpus `data/public_claims.jsonl` (14 claim), `config/pricing.yaml`, evaluator `lab8.metrics`, SQLite mới cho mỗi trial. Biến duy nhất được thay đổi: topology — có hay không lớp orchestrator + investigator (shape A → C) |
| FAILURE / METRIC | Một lỗi dự kiến và cách đo nó: pass rate, pass^5, variance, cost/success, leak, bypass | Lỗi dự kiến: chi phí phối hợp (investigator đọc lại dữ liệu workflow đã đọc) làm tăng cost mà không tăng pass. Đo bằng cost/success và mean tool calls; kiểm tra thêm pass rate, pass^5, variance để chắc chất lượng không đổi |

## Kết quả ablation

- Lệnh đã chạy (copy nguyên văn): `python -m lab8.benchmark --shapes workflow,orchestrator --cases data/public_claims.jsonl --seeds 11,22,33,44,55 --out reports/ablation_r1.json` (chạy trong `src/`)
- Run id / file report: `src/reports/ablation_r1.json` (140 trial; ví dụ `R-workflow-C-014-s11`, `R-orchestrator-C-014-s11`), đối chiếu với `src/reports/benchmark.json`
- Kết quả so với hypothesis (đúng / sai / không kết luận được), kèm số liệu: **Đúng.** Pass rate 1.000 → 1.000, pass^5 1.000 → 1.000, variance 0 → 0 (không cải thiện). Cost/success 28.86 → 56.52 VND (×1.96, trong khoảng dự đoán 1.5–2.5). Mean tool calls 2.79 → 5.57 (×2.0), mean model calls 1.00 → 0.86. Chênh lệch chi phí đến từ tool call lặp của investigator, không phải từ model. Kết luận chỉ đúng cho task tuần tự này; chưa kiểm được phần "task song song thì multi-agent có lợi" của paper vì corpus không có claim nào cần tra song song
- Giới hạn: MockLLM không phải model sản xuất, latency là `unavailable`. Corpus chỉ 14 claim public; MockLLM không mắc lỗi hiểu sai ngôn ngữ như model thật, nên lợi ích kiểm chứng chéo của multi-agent (nếu có) không xuất hiện trong đo đạc này.

Muốn đi xa hơn một ablation để lấy điểm cộng thì xem [docs/bonus_topics.md](../../docs/bonus_topics.md).
