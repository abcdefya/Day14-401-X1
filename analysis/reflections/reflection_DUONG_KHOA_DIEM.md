# Báo cáo cá nhân - Dương Khoa Điềm
## 1. Thông tin commit dùng làm bằng chứng

### Commit 1: `5b9ddc7`

- **Author:** diembattu `<duongkhoadiemp@gmail.com>`
- **Date:** Tue Apr 21 16:34:11 2026 +0700
- **Message:** `runner`
- **Files thay đổi:**
  - `engine/runner.py` — 56 insertions(+), 32 deletions(-)
- **Mô tả:** Xây dựng và hoàn thiện toàn bộ `BenchmarkRunner` với async batch runner, tích hợp `RetrievalEvaluator` + multi-judge (`evaluate_multi_judge`) vào một pipeline duy nhất. Refactor từ skeleton template sang production-ready code với output dict chuẩn hóa và `asyncio.gather()` cho concurrent batch execution.

---

### Commit 2: `724a983`

- **Author:** diembattu `<duongkhoadiemp@gmail.com>`
- **Date:** Tue Apr 21 17:45:01 2026 +0700
- **Message:** `chat`
- **Files thay đổi:**
  - `chat.py` — 229 insertions(+)
- **Mô tả:** Xây dựng từ đầu toàn bộ giao diện Streamlit chat cho phép so sánh V1 vs V2 real-time. Bao gồm `load_resources()` (cache_resource), hàm `ask_both()` async dual-agent + dual-judge, `render_result_card()`, `render_judge_metrics()`, session state history, sidebar, và delta score display.

---

## 👤 2. Điểm Cá Nhân (Tối đa 40 điểm)

---

### 2.1 Engineering Contribution (15 điểm)

#### Các module tôi đảm nhận

Trong dự án này, tôi chịu trách nhiệm chính cho **2 module kỹ thuật cốt lõi**:

#### 📄 `engine/runner.py` — Async Benchmark Runner

File này tôi xây dựng từ đầu với mục tiêu tạo ra một pipeline benchmark bất đồng bộ, xử lý test case theo từng batch để tránh vượt giới hạn rate limit của API.

**Những gì tôi đã làm:**

- **Class `BenchmarkRunner`**: Thiết kế class nhận vào một `agent` và một `LLMJudge`, tích hợp cả `RetrievalEvaluator` bên trong để đánh giá tập trung tại một nơi.
- **`run_single_test(test_case)`**: Hàm async chạy một test case hoàn chỉnh theo 3 bước tuần tự nhưng các bước độc lập có thể chạy song song:
  1. Gửi câu hỏi vào RAG agent và đo latency bằng `time.perf_counter()`.
  2. Tính toán **Hit Rate** và **MRR** từ `retrieved_ids` trả về vs `expected_retrieval_ids` trong dataset.
  3. Gọi **Multi-Judge** (`evaluate_multi_judge`) để lấy điểm chất lượng câu trả lời.
  4. Kết hợp tất cả kết quả vào một dict chuẩn hóa, bao gồm `status = "pass" / "fail"` dựa trên ngưỡng `final_score >= 3`.
- **`run_all(dataset, batch_size=5)`**: Hàm async chia dataset thành các batch nhỏ, dùng `asyncio.gather()` để chạy song song toàn bộ test case trong một batch — giúp pipeline chạy nhanh mà không bị throttle API.

**Kỹ thuật quan trọng:**
- Dùng `asyncio.gather(*tasks)` để chạy concurrent trong từng batch.
- Thiết kế output dict chuẩn với đầy đủ `ragas.retrieval.hit_rate`, `ragas.retrieval.mrr`, `judge`, `latency`, `tokens_used` — dễ dàng aggregate ở tầng trên (`main.py`).

---

#### 📄 `chat.py` — Streamlit Chat UI (V1 vs V2 Live Comparison)

File này tôi xây dựng giao diện chat trực quan cho phép người dùng hỏi bất kỳ câu hỏi nào và xem kết quả từ cả hai agent V1 và V2 cùng điểm Judge theo thời gian thực.

**Những gì tôi đã làm:**

- **`load_resources()`** (cache với `@st.cache_resource`): Warm-up embedding model và ChromaDB chỉ một lần duy nhất khi khởi động session. Khởi tạo sẵn 2 agent (`v1`, `v2`) và 1 `LLMJudge` dùng chung để tránh tốn thời gian khởi tạo lại mỗi lần hỏi.
- **`ask_both(question)`** — hàm async cốt lõi:
  - Chạy song song `v1_agent.query()` và `v2_agent.query()` bằng `asyncio.gather()`.
  - Sau khi lấy được answer, chạy đồng thời `judge.evaluate_multi_judge()` cho cả V1 lẫn V2.
  - Trả về dict đầy đủ: answer, retrieved IDs, contexts, latency, tokens, judge score.
- **`render_judge_metrics(judge, version)`**: Render chi tiết điểm judge với visual bar (`█░`), agreement rate, conflict flag, và breakdown điểm từng model judge trong expander.
- **`render_result_card(data, version)`**: Render card hoàn chỉnh cho mỗi version: answer box, quick stats (score / latency / tokens), judge metrics, và retrieved context chunks trong expander.
- **Sidebar**: Liệt kê rõ models đang dùng (Agent model, Judge 1, Judge 2), nút "Clear chat history".
- **Session state**: Lưu toàn bộ lịch sử chat (`st.session_state.history`) để hiển thị lại khi re-render.
- **Delta summary**: Tính và hiển thị `V2 vs V1 score delta` bằng màu sắc (xanh nếu V2 tốt hơn, đỏ nếu thấp hơn).

**Kỹ thuật quan trọng:**
- Sử dụng `asyncio.run()` để bridge sync Streamlit với async agent/judge.
- `@st.cache_resource` để tránh re-initialization mỗi lần Streamlit re-run.
- Layout 2 cột (`st.columns(2)`) để so sánh V1 vs V2 trực quan side-by-side.

---

### 2.2 Technical Depth (15 điểm)

#### Giải thích các khái niệm kỹ thuật

**MRR (Mean Reciprocal Rank):**  
MRR đo mức độ chunk liên quan xuất hiện *sớm* trong kết quả retrieval. Công thức: `MRR = 1 / position_of_first_relevant_chunk`. Ví dụ: nếu chunk đúng xuất hiện ở vị trí 1 → MRR = 1.0; ở vị trí 2 → MRR = 0.5; ở vị trí 3 → MRR = 0.33. MRR = 0.0 nếu không tìm thấy chunk nào đúng. Chỉ số này quan trọng vì LLM thường chú ý nhiều hơn vào context ở đầu prompt — nếu chunk đúng ở vị trí cao, answer quality sẽ tốt hơn.

**Cohen's Kappa:**  
Cohen's Kappa đo mức độ đồng thuận giữa hai judge *vượt qua khả năng xảy ra ngẫu nhiên*. Khác với agreement rate đơn giản (tỉ lệ hai judge cùng điểm), Kappa điều chỉnh theo xác suất đồng thuận ngẫu nhiên — cho phép đánh giá thực sự độ tin cậy của multi-judge system. Kappa ≥ 0.6 thường được coi là đồng thuận tốt.

**Position Bias:**  
Hiện tượng LLM judge có xu hướng đánh giá cao hơn câu trả lời xuất hiện *trước* trong prompt so với cùng nội dung xuất hiện sau. Trong `llm_judge.py`, hàm `check_position_bias()` kiểm tra điều này bằng cách gọi judge 2 lần với thứ tự A→B và B→A, nếu `|score_AB - score_BA| > 0.5` thì bị phát hiện bias.

**Trade-off: Chi phí vs Chất lượng:**  
- Dùng 2 judge model (Groq `llama-3.3-70b-versatile` + `openai/gpt-oss-120b`) tăng chi phí gấp đôi nhưng tăng độ tin cậy đánh giá vì có cơ chế phát hiện xung đột.
- Batch size nhỏ hơn (5) → ít token đồng thời → giảm nguy cơ rate limit nhưng tăng tổng thời gian; batch size lớn hơn (20 như trong `main.py`) → nhanh hơn nhưng tốn token đồng thời nhiều hơn.
- Trong `chat.py`, dùng shared `LLMJudge` instance để tái sử dụng client Groq, giảm overhead khởi tạo.

---

### 2.3 Problem Solving (10 điểm)

#### Các vấn đề tôi gặp phải và cách giải quyết

**Vấn đề 1: Streamlit không tương thích với event loop async sẵn có**  
Streamlit chạy trên main thread của Python và không có event loop async mặc định. Khi tôi dùng `await` trực tiếp trong handler, code bị lỗi `RuntimeError: no current event loop`. Giải pháp: dùng `asyncio.run(ask_both(question))` để tạo và chạy event loop mới mỗi lần có câu hỏi — đây là pattern chuẩn để bridge sync và async trong Streamlit.

**Vấn đề 2: Khởi tạo model và ChromaDB tốn thời gian**  
Mỗi lần Streamlit re-render (reload page, clear history, ...) sẽ chạy lại code từ đầu, dẫn đến việc load lại embedding model và ChromaDB mất vài giây. Giải pháp: dùng `@st.cache_resource` cho hàm `load_resources()` — Streamlit cache object này xuyên suốt session, model chỉ load một lần duy nhất.

**Vấn đề 3: Rate limit khi benchmark nhiều test case đồng thời**  
Khi dùng `asyncio.gather()` cho toàn bộ 50 test case cùng lúc, API trả về 429 Rate Limit. Giải pháp trong `runner.py`: chia dataset thành batch nhỏ (`batch_size=5` mặc định), chạy song song trong batch, hoàn thành batch rồi mới chạy batch tiếp theo. Cách này cân bằng được tốc độ và tránh rate limit.

**Vấn đề 4: Judge trả về JSON lẫn markdown fences**  
LLM đôi khi bọc JSON trong ``` code block ``` thay vì trả về JSON thuần. Hàm `_parse_score()` trong `llm_judge.py` xử lý bằng cách strip markdown fences trước khi `json.loads()`, đảm bảo parsing không bị lỗi.

**Vấn đề 5: Hiển thị lịch sử chat sau khi Streamlit re-render**  
Sau khi submit câu mới, Streamlit re-render toàn bộ page. Nếu không lưu lịch sử, mọi câu hỏi cũ sẽ biến mất. Giải pháp: append mỗi `result` vào `st.session_state.history` và render lại toàn bộ history ở đầu page mỗi lần re-render.

---

## Tổng kết

| Hạng mục | Mô tả đóng góp | Điểm tự đánh giá |
|:---|:---|:---:|
| **Engineering Contribution** | Xây dựng `engine/runner.py` (async batch runner, full pipeline) và `chat.py` (Streamlit UI với async dual-agent + dual-judge real-time). | 13 / 15 |
| **Technical Depth** | Hiểu và giải thích được MRR, Position Bias, Cohen's Kappa, trade-off Cost vs Quality qua thiết kế thực tế của code. | 13 / 15 |
| **Problem Solving** | Giải quyết được 5 vấn đề thực tế: async/sync bridge, cache resource, rate limit batching, JSON parsing, session state. | 9 / 10 |
| **Tổng** | | **35 / 40** |
