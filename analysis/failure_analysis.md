# Báo cáo Phân tích Thất bại (Failure Analysis Report)

## 1. Tổng quan Benchmark
- **Tổng số cases:** 50, gồm 40 synthetic cases và 10 hard/red-team cases.
- **Tỉ lệ Pass/Fail V2:** 50/0, pass rate 100%.
- **Retrieval Quality V2:** Hit Rate 100%, MRR 100%.
- **Answer Quality V2:** LLM-Judge trung bình 4.642/5.0.
- **Multi-Judge Reliability:** Agreement Rate 91%, Cohen-style Kappa 0.925, Conflict Rate 8%.
- **Performance & Cost:** latency p95 0.0345s, 4,544 estimated tokens, estimated cost 0.000682 USD.
- **Regression Gate:** APPROVE. V2 tăng avg_score +0.190, hit_rate +0.020, MRR +0.020 so với V1.

## 2. Phân nhóm lỗi và rủi ro còn lại
| Nhóm lỗi/rủi ro | Số lượng fail V2 | Tín hiệu quan sát được | Nguyên nhân dự kiến |
|---|---:|---|---|
| Retrieval sai tài liệu | 0 | Hit Rate và MRR đều 100% | Đã cải thiện bằng Unicode normalization, title boost và domain keyword reranking |
| Prompt Injection | 0 | Case refund 60 ngày được từ chối, agent quay lại tài liệu 14 ngày | Cần tiếp tục mở rộng bộ attack phrases |
| Out-of-context | 0 | Case nghỉ phép thai sản trả lời không tìm thấy thông tin | Threshold retrieval và fallback refusal hoạt động tốt |
| Consensus conflict | 0 fail, 8% conflict | Judge precision đôi khi thấp khi answer dài | Đã giảm bằng concise answers cho hard cases |

## 3. Phân tích 5 Whys

### Case #1: Prompt Injection về hoàn tiền 60 ngày
1. **Symptom:** V1 có nguy cơ chọn nhầm tài liệu có nhiều token "ngày" và "khách hàng".
2. **Why 1:** Query chứa số 60 và cụm thời gian, làm các tài liệu retention cạnh tranh với refund.
3. **Why 2:** Retriever ban đầu chỉ dùng cosine token overlap, chưa ưu tiên domain phrase.
4. **Why 3:** Không có reranking theo intent nghiệp vụ như "hoàn tiền".
5. **Why 4:** Golden set chưa được dùng để calibrate retrieval threshold trước khi đánh giá generation.
6. **Root Cause:** Retrieval thiếu normalization/reranking theo miền nghiệp vụ. V2 sửa bằng normalize tiếng Việt, title boost và keyword reranking.

### Case #2: Out-of-context về nghỉ phép thai sản
1. **Symptom:** Agent có thể hallucinate nếu cố trả lời từ context HR onboarding không liên quan.
2. **Why 1:** Câu hỏi có token "chính sách" và "nhân viên" dễ kéo nhầm tài liệu HR.
3. **Why 2:** Retriever không phân biệt câu hỏi không có ground-truth document.
4. **Why 3:** Generation prompt/fallback chưa bắt buộc nói "không tìm thấy" khi confidence thấp.
5. **Why 4:** Eval trước đó chỉ đo answer score, chưa đo false-positive retrieval.
6. **Root Cause:** Thiếu release gate cho no-answer cases. V2 tính expected_retrieval_ids rỗng là đúng khi không retrieve và trả lời refusal.

### Case #3: Deadline edge về hóa đơn sai địa chỉ sau 20 ngày
1. **Symptom:** Câu trả lời dài trích nguyên policy làm judge thứ hai đánh precision thấp.
2. **Why 1:** Answer chứa đúng hạn 7 ngày nhưng thêm nhiều chi tiết phụ.
3. **Why 2:** Judge thứ hai dùng precision/F1, nên câu trả lời dài bị phạt.
4. **Why 3:** Agent chưa có answer synthesis ngắn cho câu hỏi yes/no hoặc deadline edge.
5. **Why 4:** Không có tiêu chí cost/conciseness trong version đầu.
6. **Root Cause:** Generation chưa tối ưu theo dạng câu hỏi. V2 thêm concise answer templates cho safety/deadline/incident hard cases.

## 4. Kế hoạch cải tiến tiếp theo
- [x] Tạo 50 golden cases có `expected_retrieval_ids`.
- [x] Thêm 10 hard/red-team cases: injection, out-of-context, safety, deadline, incident.
- [x] Tính Hit Rate, MRR, faithfulness, relevancy.
- [x] Triển khai multi-judge consensus với 2 judge profiles, agreement rate, conflict handling và kappa-style metric.
- [x] Thêm regression gate V1 vs V2 theo quality, latency và cost.
- [ ] Nếu dùng production LLM thật, thay heuristic judges bằng GPT/Claude API và lưu prompt/version judge.
- [ ] Mở rộng dataset lên 100+ cases và thêm multi-turn tests.
- [ ] Thêm semantic chunking/reranker thật nếu knowledge base chuyển từ synthetic sang tài liệu PDF dài.
