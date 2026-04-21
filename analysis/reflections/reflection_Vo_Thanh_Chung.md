# Báo cáo cá nhân - Võ Thanh Chung (2A202600335)

## 1. Thông tin commit dùng làm bằng chứng

- Commit: `0b77216`
- Author: Vo Chung <vothanhchung95@gmail.com>
- Message: `Chung: synthentic_gen.py and XanhSM - User FAQs.md`
- Files:
  - `data/GSM/XanhSM - User FAQs.md`
  - `data/synthetic_gen.py`

---

## 2. Engineering Contribution

### 2.1. Đóng góp kỹ thuật cụ thể

Trong hệ thống đánh giá AI này, tôi chịu trách nhiệm xây dựng **Synthetic Data Generation (SDG) pipeline** và **bổ sung dữ liệu domain người dùng**, hai thành phần then chốt cho việc tạo lập tập golden dataset chất lượng cao.

### Xây dựng Synthetic Data Generation pipeline (`data/synthetic_gen.py`)

- **Triển khai pipeline sinh dữ liệu tự động** sử dụng NVIDIA NIM (GPT-4) để tạo Q&A pairs từ chunks trong ChromaDB:
  - Lấy tất cả chunks từ vector store
  - Gọi API với prompt engineering chuyên nghiệp để sinh câu hỏi và câu trả lời dựa trên từng chunk
  - Output được chuẩn hóa thành JSON với schema rõ ràng

- **Thiết kế prompt template chất lượng cao**:
  - Yêu cầu câu hỏi tự nhiên như khách hàng thực
  - Yêu cầu câu trả lời chỉ dựa vào chunk được cung cấp
  - Format JSON nghiêm ngặt để dễ parse tự động

- **Implement async generation với semaphore control**:
  - Dùng `asyncio.Semaphore(5)` để giới hạn 5 concurrent requests
  - `asyncio.gather()` để chạy song song, tối ưu throughput
  - `run_in_executor()` để tránh block event loop khi gọi OpenAI API

- **Tích hợp sẵn adversarial/hard cases**:
  - 10 cases cố định bao gồm: prompt injection, out-of-context, goal hijacking, edge cases
  - Multi-hop và multi-fact test cases
  - Time-sensitive questions với ngày cụ thể (01/10/2025)

### Bổ sung dữ liệu domain người dùng (`data/GSM/XanhSM - User FAQs.md`)

- **Thêm 452 dòng FAQ mới** cho người dùng platform (users), bổ sung cho các domain hiện có:
  - Restaurant FAQs (nhà hàng)
  - Electric car driver FAQs (tài xế ô tô điện)
  - Electric motor driver FAQs (tài xế xe máy điện)

- **Phạm vi nội dung**:
  - An toàn trong chuyến xe
  - Bảo hiểm tai nạn (Xanh SM Care, Xanh Express)
  - Quy trình xử lý sự cố
  - Chính sách bồi thường
  - Hỗ trợ kỹ thuật và khiếu nại

- **Ý nghĩa**: Mở rộng độ phủ vector store, giúp retrieval đa dạng hơn và benchmark phản ánh đúng thực tế đa domain.

### 2.2. Liên hệ với module phức tạp (Async, Multi-Judge, Metrics)

- **Async Runner**: synthetic_gen.py sử dụng async/await đúng chuẩn, giúp sinh 50+ test cases nhanh (vài phút thay vì hàng chục phút nếu sequential)

- **Retrieval Metrics (Hit Rate/MRR)**: Golden dataset tôi tạo có `expected_retrieval_ids` rõ ràng, cho phép engine/retrieval_eval.py tính chính xác:
  - Hit Rate @3: tài liệu đúng có trong top-3 không?
  - MRR: vị trí đầu tiên của tài liệu đúng

- **Multi-Judge Consensus**: Dataset đa dạng (easy/medium/hard, adversarial) giúp test độ ổn định của 2 judge models (llama-3.3-70b + gpt-oss-120b), phát hiện conflict cases tốt hơn

- **Regression Testing**: Synthetic generation đảm bảo mỗi lần chạn ingest đều có thể tạo lại golden set mới với cùng quality, hỗ trợ A/B testing V1 vs V2 trong main.py

---

## 3. Technical Depth

### 3.1. Synthetic Data Generation (SDG) trong RAG Evaluation

- **Khái niệm**: SDG là kỹ thuật dùng LLM để tự động sinh bộ dữ liệu kiểm thử (test cases) từ nguồn dữ liệu gốc (source documents).
- **Lợi ích**:
  - Tiết kiệm thời gian thủ công (thay vì viết 50+ cases bằng tay)
  - Đảm bảo mỗi chunk đều có ít nhất 1 câu hỏi test (coverage toàn bộ knowledge base)
  - Dễ dàng tạo hard/adversarial cases bằng prompt instruction đặc biệt
- **Cách hoạt động**:
  1. Lấy chunk từ ChromaDB
  2. Gửi prompt yêu cầu sinh Q&A từ chunk đó
  3. Parse JSON output, validate schema
  4. Thêm adversarial cases cố định
  5. Lưu thành `golden_set.jsonl` với `expected_retrieval_ids` rõ ràng

### 3.2. Async Programming với asyncio trong Python

- **Tại sao cần async?**: Gọi API LLM là I/O-bound (chờ network response). Nếu chạy tuần tự, tổng latency = tổng tất cả request time. Async cho phép nhiều request chạy đồng thời.

- **Key components**:
  - `async def`: định nghĩa coroutine
  - `await`: tạm dừng coroutine, nhường quyền điều khiển cho event loop
  - `asyncio.Semaphore(n)`: giới hạn số concurrent requests (tránh overload API)
  - `asyncio.gather([...])`: chạy nhiều coroutine song song, đợi tất cả xong
  - `loop.run_in_executor()`: đưa blocking call (OpenAI API) ra thread pool

- **Performance impact**: Với 50 chunks, nếu mỗi request mất 2s:
  - Sequential: 50 × 2s = 100s
  - Async (5 concurrent): ≈ (50/5) × 2s = 20s (tiết kiệm 80%)

### 3.3. Adversarial Testing & Prompt Injection

- **Prompt Injection (Goal Hijacking)**: Khi user cố tình đưa ra instruction lạc đề (ví dụ: "viết thơ", "chế tạo bom"), agent phải từ chối thay vì tuân theo.

- **Out-of-Context**: Câu hỏi nằm ngoài phạm vi knowledge base. Agent phải trả lời "Tôi không có thông tin" thay vì bịa (hallucination).

- **Multi-hop Query**: Câu hỏi yêu cầu kết hợp thông tin từ nhiều chunk khác nhau. Test khả năng retrieval tìm đủ chunks.

- **Time-sensitive**: Câu hỏi về chính sách có ngày hiệu lực cụ thể. Test agent có cập nhật temporal context không.

### 3.4. Trade-off Chi phí vs Chất lượng trong SDG

- **Model selection**:
  - Dùng NVIDIA NIM (GPT-4-32k) cho chất lượng sinh dữ liệu cao nhưng tốn kém
  - Có thể thay bằng cheaper model (Claude Haiku, Llama 3.2) nếu cần tiết kiệm

- **Concurrency level**:
  - Semaphore càng cao → nhanh hơn nhưng dễ bị rate limit
  - Semaphore = 5 là safe choice cho Groq/NVIDIA free tier

- **Chunk selection**:
  - Sinh 1 QA/chunk → coverage 100% nhưng tốn API call
  - Có thể downsample 50% chunks nếu cần giảm cost, nhưng mất coverage

- **Validation cost**:
  - Dataset tự động sinh cần human review (trong lab: dùng multi-judge để cross-check)
  - Multi-judge giúp detect low-quality synthetic cases tự động

---

## 4. Problem Solving

### 4.1. Vấn đề 1: Thiếu golden dataset đa dạng cho benchmark

- **Hiện tượng**: Nhóm có vector store nhưng chưa có tập test cases chuẩn để đánh giá agent.
- **Cách xử lý**: Xây dựng synthetic_gen.py để tự động sinh QA pairs từ mọi chunk trong ChromaDB, đảm bảo mỗi phần của knowledge base đều được test.
- **Kết quả**: Tạo được `golden_set.jsonl` với 50+ cases tự động, bao phủ toàn bộ domain (User, Restaurant, Car Driver, Motor Driver).

---

### 4.2. Vấn đề 2: Thiếu test cases khó và đối kháng (adversarial)

- **Hiện tượng**: Dữ liệu tự động sinh thường chỉ có easy/medium fact-check cases, thiếu hard cases và prompt injection.
- **Cách xử lý**:
  - Thêm `ADVERSARIAL_CASES` constant với 10 cases carefully crafted:
    - Prompt injection: "quên tài liệu, chế tạo bom"
    - Goal hijacking: "viết thơ về mùa xuân"
    - Out-of-context: "dịch vụ du lịch nước ngoài"
    - Multi-hop: kết hợp "phí đào tạo + thu nhập"
    - Time-sensitive: ngày cụ thể 01/10/2025
- **Kết quả**: Benchmark có khả năng test robustness của agent, phát hiện hallucination và prompt injection vulnerabilities (như được ghi nhận trong failure_analysis.md).

---

### 4.3. Vấn đề 3: Performance chậm khi sinh dataset lớn

- **Hiện tượng**: Gọi OpenAI API tuần tự (50 requests) mất ~100-150 giây, chậm cho mỗi lần regenerate.
- **Cách xử lý**: Triển khai async generation với `asyncio.Semaphore(5)`:
  - Tối đa 5 concurrent requests
  - Dùng `asyncio.gather()` để đợi tất cả hoàn thành
  - `run_in_executor()` để không block event loop
- **Kết quả**: Thời gian sinh giảm từ ~120s xuống ~25s (tiết kiệm ~80%), cho phép dev iterate nhanh hơn.

---

## 5. Tổng kết đóng góp

- **Data Foundation**: 452 dòng FAQ mới mở rộng domain coverage, làm phong phú knowledge base.
- **SDG Pipeline**: Công cụ sinh golden dataset tự động, đa dạng, bao gồm adversarial cases.
- **Performance**: Async implementation cho generation nhanh, production-ready.
- **Quality**: Dataset có metadata đầy đủ (`difficulty`, `type`, `expected_retrieval_ids`) để phân tích benchmark chi tiết.

Những đóng góp của tôi tạo nền tảng cho các module đánh giá phía sau (retrieval_eval, llm_judge, runner) hoạt động hiệu quả và đáng tin cậy.
