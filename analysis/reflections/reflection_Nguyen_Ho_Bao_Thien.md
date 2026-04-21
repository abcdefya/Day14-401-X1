# Báo cáo cá nhân - Nguyễn Hồ Bảo Thiên (2A202600163)

## 1. Thông tin commit dùng làm bằng chứng

- Commit: `019202f`
- Author: thiennguyen37-qn
- Message: `Add retrieval_eval.py and llm_judge.py`
- Files:
  - `engine/retrieval_eval.py`
  - `engine/llm_judge.py`


## 2. Engineering Contribution

### 2.1. Đóng góp kỹ thuật cụ thể

Trong hệ thống này, tôi tập trung đóng góp vào hai module chính: Multi-Judge Evaluation Engine và Retrieval Metrics Evaluator

### Đối với LLM-Judge:
- Xây dựng cơ chế đánh giá song song (async) sử dụng asyncio + run_in_executor để gọi 2 LLM judges:
    - Model 1: llama-3.3-70b-versatile
    - Model 2: openai/gpt-oss-120b

- Thiết kế rubric chấm điểm chuẩn hóa (1–5) dựa trên Ground Truth
    - Implement cơ chế Conflict detection nếu |score₁ - score₂| > 1
    - Final score: trung bình 2 judge
    - Agreement rate: 1 nếu không conflict, ngược lại 0

- Implement hàm check_position_bias() nhằm phát hiện liệu LLM judge bị ảnh hưởng bởi thứ tự input hay không.

### Đối với Retrieval evaluation:

- Xây dựng evaluator đo chất lượng retrieval:
Hit Rate, MRR (Mean Reciprocal Rank)
- Thiết kế pipeline: Agent trả về retrieved_ids
So sánh với expected_retrieval_ids



---

## 3. Technical Depth

### 3.1. MRR (Mean Reciprocal Rank)

- Ý nghĩa: đo vị trí xuất hiện của tài liệu đúng đầu tiên trong danh sách truy xuất.
- Công thức: `MRR = 1/rank` với `rank` là vị trí tài liệu đúng đầu tiên (1-indexed), không tìm thấy thì bằng 0.
- Tác dụng: phản ánh retrieval “đúng và sớm”, quan trọng cho RAG vì context đầu danh sách ảnh hưởng mạnh đến câu trả lời.

### 3.2. Hit Rate
- Ý nghĩa: Đo lường tỷ lệ phần trăm các truy vấn mà hệ thống tìm thấy ít nhất một tài liệu đúng trong top $k$ kết quả trả về. Công thức:$$\text{Hit Rate} = \frac{\text{Số lượng truy vấn có kết quả đúng trong Top } k}{\text{Tổng số lượng truy vấn}}$$(Trong đó $k$ là số lượng tài liệu được lấy ra).

- Tác dụng: Phản ánh "độ bao phủ" (coverage) của hệ thống retrieval. Trong quy trình RAG, Hit Rate cực kỳ quan trọng vì nó đóng vai trò là "màng lọc" đầu tiên. Nếu Hit Rate thấp, tài liệu đúng thậm chí không lọt được vào ngữ cảnh (context) để LLM đọc, dẫn đến việc mô hình chắc chắn sẽ trả lời sai hoặc gây ra hiện tượng ảo giác (hallucination)


### 3.3. Position Bias
 - Ý nghĩa: Hiện tượng hiệu suất của mô hình ngôn ngữ lớn (LLM) bị ảnh hưởng bởi vị trí của tài liệu đúng trong ngữ cảnh đầu vào. Mô hình thường chú ý tốt hơn đến thông tin ở đầu hoặc cuối danh sách (Primacy & Recency bias) và bỏ sót thông tin ở giữa.
 - Hiện tượng: Thường được minh họa bằng biểu đồ hình chữ "U" (còn gọi là hiện tượng Lost in the Middle), mô tả việc độ chính xác giảm mạnh khi tài liệu quan trọng nằm ở giữa các đoạn ngữ cảnh được cung cấp.
 - Tác dụng: Cảnh báo rằng việc tăng số lượng tài liệu lấy ra ($k$) không phải lúc nào cũng tốt. Trong RAG, việc sắp xếp tài liệu có độ liên quan cao nhất lên đầu (re-ranking) là cực kỳ quan trọng để khắc phục định kiến này, giúp LLM không "quên" mất thông tin quan trọng khi phải đọc quá nhiều tài liệu cùng lúc.

### 3.4. Trade-off Chi phí vs Chất lượng

- Embedding model lớn hơn -> thường tăng chất lượng retrieval nhưng tăng chi phí và thời gian ingest.
- Chunk nhỏ -> tăng recall nhưng có thể giảm precision, số vector nhiều hơn làm tốn tài nguyên.
- Re-rank hoặc multi-judge -> tăng độ tin cậy nhưng tăng latency/cost.
- Cân bằng thực tế: chọn chunking theo section + model multilingual vừa phải để đạt chất lượng tốt trong ngân sách lab.

---

## 4. Problem Solving

### 4.1. Tối ưu hóa hiệu năng với lập trình bất đồng bộ (Asyncio)
- Vấn đề: Khi đánh giá một tập dữ liệu lớn, việc gọi API đến các LLM (Groq) theo cách tuần tự (sequential) gây ra độ trễ cực lớn, khiến quá trình đánh giá mất nhiều thời gian.
- Giải pháp: Sử dụng asyncio.gather và run_in_executor trong llm_judge.py. Việc này cho phép gọi đồng thời (concurrently) cả hai Judge (Llama 3.3 và GPT-OSS), giúp giảm thời gian phản hồi xuống chỉ còn bằng thời gian của mô hình chậm nhất thay vì tổng thời gian của cả hai.

### 4.2. Xử lý tính không ổn định của dữ liệu đầu ra (Robust JSON Parsing)
- Vấn đề: LLM đôi khi trả về kết quả bao gồm cả lời dẫn hoặc định dạng Markdown (ví dụ: json ... ), gây lỗi khi sử dụng hàm json.loads() tiêu chuẩn.
- Giải pháp: Xây dựng hàm _parse_score với logic làm sạch dữ liệu mạnh mẽ:
    - Loại bỏ các ký tự thừa và khối code block Markdown.
    - Sử dụng cơ chế "rào chắn" (max(1, min(5, ...))) để đảm bảo điểm số luôn nằm trong thang 1-5 bất kể sai sót nhỏ từ phía LLM.

### 4.3. Giải quyết mâu thuẫn giữa các quan điểm (Conflict Resolution)
- Vấn đề: Một Judge duy nhất có thể bị thiên kiến (bias) hoặc nhầm lẫn. Làm sao để biết kết quả đánh giá là đáng tin cậy?
- Giải pháp: * Triển khai cơ chế Multi-Judge Consensus. Hệ thống tính toán agreement_rate dựa trên độ lệch điểm số ($|score_A - score_B| \le 1$). Nếu độ lệch $> 1$, hệ thống tự động gắn cờ conflict, giúp người vận hành dễ dàng lọc ra các trường hợp cần sự can thiệp của con người để kiểm tra lại.

### 4.4. Xử lý các trường hợp biên trong Retrieval (Edge Cases)
- Vấn đề: Trong các bộ dữ liệu thực tế, có những câu hỏi "adversarial" (đối kháng) hoặc ngoài ngữ cảnh mà không có tài liệu đúng (expected_ids rỗng).
- Giải pháp: Trong retrieval_eval.py, logic được thiết kế để trả về 1.0 nếu không có tài liệu nào được kỳ vọng tìm thấy. Điều này giúp phản ánh đúng bản chất: nếu không có gì để tìm và hệ thống không tìm bừa, thì đó là một kết quả đúng.

