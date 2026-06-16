# Reflection - Nguyen Duc Khang

## Đóng góp kỹ thuật
- Hoàn thiện evaluation pipeline offline có thể chạy tự động bằng `python main.py`.
- Xây dựng golden dataset 50 cases với `expected_retrieval_ids`, gồm 10 hard/red-team cases.
- Triển khai RAG agent deterministic có retrieval IDs, Unicode normalization cho tiếng Việt, title boost và keyword reranking.
- Triển khai RetrievalEvaluator với Hit Rate, MRR, faithfulness và relevancy.
- Triển khai Multi-Judge consensus gồm 2 judge profiles, agreement rate, conflict handling và kappa-style metric.
- Thêm regression release gate so sánh V1/V2 theo score, retrieval, latency và estimated cost.

## Technical Depth
- **MRR:** đo vị trí tài liệu đúng đầu tiên; nếu tài liệu đúng đứng hạng 1 thì MRR = 1, hạng 2 thì 0.5.
- **Hit Rate:** đo việc có ít nhất một ground-truth document xuất hiện trong top-k retrieval hay không.
- **Cohen's Kappa:** dùng để ước lượng mức đồng thuận giữa judges sau khi loại bớt đồng thuận ngẫu nhiên; trong repo dùng biến thể bucketed/weighted để mô phỏng.
- **Position Bias:** judge có thể thiên vị câu trả lời xuất hiện trước; cần kiểm tra bằng cách đổi thứ tự response A/B.
- **Cost vs Quality:** concise answers giúp giảm token/cost và còn tăng precision của judge, nhưng cần giữ đủ bằng chứng để không mất faithfulness.

## Bài học và hướng cải tiến
- Với tiếng Việt, tokenizer ASCII làm retrieval sai nghiêm trọng; Unicode normalization là bước bắt buộc.
- Không nên chỉ đo answer quality. Retrieval metrics phát hiện lỗi trước khi generation che lấp nguyên nhân.
- Hard cases giúp tìm lỗi thật: prompt injection, out-of-context và deadline edge đều cần logic riêng.
- Nếu triển khai production, cần thay heuristic judge bằng multi-model LLM thật, lưu raw judge output và audit conflict cases thủ công.
