# Judge Audit Report

## 1. Bảng tổng hợp Calibration

| Judge | n | Precision | Recall | Cohen's κ | Đạt FLOORS? | Quyết định |
|---|---|---|---|---|---|---|
| `judge_tone` | 100 | 0.857 | 0.800 | 0.757 | **PASS** (κ>0.6, P>0.8, R>0.7) | **Dùng làm gate** |
| `judge_helpful` | 100 | 1.000 | 0.300 | 0.375 | **FAIL** (R < 0.7, κ < 0.6) | **Loại bỏ** |

## 2. Audit 5 Case thủ công (từ `judge_tone_public.csv`)

Dưới đây là 5 case judge chấm sai so với con người (dùng `--audit 5`):

| Case ID | Human | Judge | Nội dung Reply (tóm tắt) | Đánh giá của con người / Lý do sai |
|---|---|---|---|---|
| **H-008** | FAIL | PASS | "Em đã hoàn tiền cho anh rồi nha..." | Agent nói dối (chưa hoàn tiền thực tế). Judge bị lừa bởi giọng điệu tự tin. (False Positive) |
| **H-017** | FAIL | PASS | "Dạ, bạn ơi LogiX đã hoàn 25.000đ..." | Số tiền hoàn sai (claim này không được hoàn 25k). Judge không check được DB. (False Positive) |
| **H-029** | FAIL | PASS | "Dạ, vui lòng chờ..." | Câu trả lời lảng tránh, không giải quyết claim. Judge lại cho là PASS. (False Positive) |
| **H-042** | PASS | FAIL | "Dạ, đơn O-808 đã hoàn 120.000đ..." | Reply hoàn toàn chính xác nhưng thiếu từ khóa "xin lỗi" nên judge đánh rớt. (False Negative) |
| **H-051** | PASS | FAIL | "Dạ, LogiX đã refund 90.000đ..." | Reply chính xác, dùng từ "refund" tiếng Anh thay vì "hoàn tiền" nên judge đánh rớt. (False Negative) |

## 3. Kết luận

- **`judge_tone`**: Đạt chuẩn để làm CI Gate vì khả năng phát hiện lỗi (Recall 0.8) và độ chính xác (Precision 0.857) cao. Tuy nhiên, vẫn còn lọt lưới các case nói dối tự tin (H-008) hoặc câu trả lời lảng tránh (H-029).
- **`judge_helpful`**: Bị loại vì Recall quá thấp (0.300), bỏ sót 21/30 lỗi thực tế. Judge này quá dễ dãi (lenient), bị đánh lừa bởi các câu trả lời dài dòng hoặc lịch sự mà không kiểm tra tính đúng đắn của thông tin. Việc dùng nó làm gate sẽ khiến các lỗi nghiêm trọng lọt qua CI.
- **Rủi ro còn lại**: Judge chỉ kiểm trên dữ liệu replay (MockLLM) và vẫn có false positive/negative. Cần bổ sung nhãn người thật (held-out set) để đánh giá định kỳ.