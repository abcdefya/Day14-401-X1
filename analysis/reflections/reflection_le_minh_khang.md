# Báo cáo cá nhân - Lê Minh Khang

## 1. Thông tin commit dùng làm bằng chứng

- Commit 1: `989120b`
- Author: `khang <minhkhangle2k4@gmail.com>`
- Message: `Add EDA report for golden_set.jsonl`
- Files:
  - `analysis/golden_set_eda.md`

- Commit 2: `b7672bd`
- Author: `Khang Lê <114637968+Khang-Water@users.noreply.github.com>`
- Message: `Refactor MainAgent for versioning and improve prompts`
- Files:
  - `agent/main_agent.py`

- Commit 3: `7d2d308`
- Author: `Khang Lê <114637968+Khang-Water@users.noreply.github.com>`
- Message: `Add files via upload`
- Files:
  - `data/GSM/XanhSM - electric_motor_driver FAQs.md`

## 2. Engineering Contribution

### 2.1. Đóng góp kỹ thuật cụ thể

Tôi phụ trách 3 phần chính trong pipeline RAG benchmark: **agent runtime**, **data domain coverage**, và **EDA baseline**.

1. Refactor `MainAgent` từ mock sang RAG thực (`agent/main_agent.py`)

- Thiết kế agent có version `v1/v2`, cho phép A/B prompt và theo dõi phiên bản trong metadata trả về.
- Thay logic giả lập bằng pipeline thật: retrieve từ ChromaDB (`top_k=3`) + generate bằng NVIDIA NIM.
- Tổ chức shared singleton (`SentenceTransformer`, Chroma collection) và `warm_up()` để giảm overhead khởi tạo khi chạy async.
- Bổ sung metadata kỹ thuật (`tokens_used`, `model`, `retrieved_ids`, `version`) để phục vụ phân tích benchmark.

2. Bổ sung dữ liệu domain cho tài xế xe máy điện (`data/GSM/XanhSM - electric_motor_driver FAQs.md`)

- Thêm bộ FAQ lớn cho nghiệp vụ tài xế xe máy điện (hồ sơ, chuyến đi, sự cố, chính sách).
- Mở rộng độ phủ retrieval cho nhóm câu hỏi vận hành thực tế thay vì chỉ tập trung taxi/restaurant/user.
- Tạo thêm nguồn để sinh hard cases và đo khả năng agent trả lời đúng trong domain mới.

3. Thiết lập baseline chất lượng dữ liệu đánh giá (`analysis/golden_set_eda.md`)

- Tổng hợp chất lượng tập `golden_set.jsonl`: schema completeness, parse health, label distribution, duplicate checks.
- Chỉ ra điểm lệch phân phối (`procedure` chiếm đa số) để tránh hiểu sai aggregate score.
- Phân tích độ dài text và mức khớp source chunk với expected retrieval IDs để hỗ trợ debug retrieval.

### 2.2. Liên hệ với module phức tạp (Async, Multi-Judge, Metrics)

- **Async Runner:** refactor agent theo executor giúp tách phần blocking I/O/compute khi chạy nhiều query.
- **Retrieval Metrics (Hit Rate/MRR):** mở rộng data motor-driver và thêm `retrieved_ids` giúp đo metric có ý nghĩa và truy vết lỗi cụ thể hơn.
- **Multi-Judge:** prompt V2 “stay-grounded” giảm nguy cơ hallucination, giúp đầu ra ổn định hơn cho hệ chấm nhiều judge.
- **Evaluation Governance:** EDA baseline giúp đọc kết quả theo từng nhóm difficulty/type thay vì chỉ nhìn điểm trung bình.

Kết luận: đóng góp của tôi trải trên cả **agent implementation + data foundation + evaluation baseline**, giúp hệ benchmark vận hành sát thực tế hơn và dễ phân tích hơn.

---

## 3. Technical Depth

### 3.1. Versioned prompt strategy cho RAG agent

- Tách `v1` và `v2` ở system prompt giúp kiểm soát thay đổi và so sánh định lượng giữa các phiên bản.
- Prompt V2 thêm ràng buộc grounded answer (“chỉ dựa vào context”) và hành vi abstain khi thiếu dữ liệu.
- Việc ghi `version` vào metadata là điều kiện cần để đánh giá regression theo vòng lặp.

### 3.2. Tối ưu runtime cho async benchmark

- Embedding model và Chroma collection được cache singleton, tránh nạp lại mỗi request.
- `warm_up()` khởi tạo trước trong main thread giúp giảm rủi ro và độ trễ cold-start.
- `run_in_executor` đưa retrieval/generation blocking ra thread pool, tránh block event loop của runner.

### 3.3. Tác động của mở rộng domain dữ liệu tới retrieval

- Dataset motor-driver tăng độ đa dạng intent (hồ sơ, quy định, xử lý sự cố, vận hành chuyến đi).
- Coverage cao hơn giúp đánh giá đúng khả năng retriever trên câu hỏi “dài và nghiệp vụ”, không chỉ câu hỏi FAQ đơn giản.
- Đồng thời tăng yêu cầu quality control vì domain mới dễ gây mismatch nếu chunking/indexing không nhất quán.

### 3.4. Vai trò của EDA trong diễn giải metric

- EDA cho thấy phân phối dữ liệu lệch, vì vậy cần báo cáo thêm theo lát cắt type/difficulty.
- Các kiểm tra uniqueness, parse error và source-id alignment giúp phân biệt lỗi do data hay do model.
- Nhờ đó việc tối ưu retriever/judge có hướng rõ ràng hơn, tránh tối ưu sai mục tiêu.

---

## 4. Problem Solving

### 4.1. Vấn đề 1: Agent template ban đầu chỉ là mô phỏng

- Hiện tượng: không thể dùng để benchmark thật vì answer/context là dữ liệu giả.
- Cách xử lý: refactor thành RAG thật với Chroma retrieval + NVIDIA NIM generation.
- Kết quả: pipeline chạy được end-to-end và trả về artifact đo lường được (`retrieved_ids`, `tokens`, `model`, `version`).

### 4.2. Vấn đề 2: Thiếu dữ liệu cho domain tài xế xe máy điện

- Hiện tượng: benchmark thiếu coverage cho nhóm câu hỏi vận hành bike driver.
- Cách xử lý: bổ sung file FAQ motor-driver với nhiều tình huống nghiệp vụ.
- Kết quả: tăng độ phủ test set và chất lượng đánh giá retrieval theo domain thực tế.

### 4.3. Vấn đề 3: Khó đọc nguyên nhân sai số khi benchmark

- Hiện tượng: khi score thấp khó kết luận do data imbalance, do retrieval hay do generation.
- Cách xử lý: xây dựng EDA report có schema checks, label distribution, text stats và alignment checks.
- Kết quả: nhóm có baseline để chẩn đoán sai số nhanh và ưu tiên đúng hạng mục cần cải thiện.
