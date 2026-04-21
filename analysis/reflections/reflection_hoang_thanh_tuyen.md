# Báo cáo cá nhân - Hoàng Thị Thanh Tuyền

## 1. Thông tin commit dùng làm bằng chứng

- Commit: `34fb363`
- Author: `starwindee <hoangthanhtuyen1412@gmail.com>` - MHV: 2A202600074
- Message: `add ingest.py and restaurant dataset`
- Files:
  - `data/ingest.py`
  - `data/GSM/XanhSM - Restaurant FAQs.md`

## 2. Engineering Contribution

### 2.1. Đóng góp kỹ thuật cụ thể

Tôi chịu trách nhiệm xây dựng tầng **Ingestion/Indexing** để phục vụ các module đánh giá phía sau (Retrieval Metrics, Multi-Judge, Async Runner):

1. Thiết kế pipeline ingest tài liệu markdown theo section

- Tách chunk theo header `##` để giữ ngữ nghĩa theo FAQ.
- Gán `chunk_id` mang tính xác định (deterministic) theo format `slug_section`.
- Kèm metadata (`source`, `section_title`) để trace lỗi khi benchmark.

2. Chuẩn hóa vector store cho retrieval evaluation

- Dùng embedding model `paraphrase-multilingual-MiniLM-L12-v2`.
- Upsert dữ liệu vào ChromaDB collection cấu hình qua biến môi trường.
- Hỗ trợ re-run idempotent bằng xóa collection cũ trước khi ghi mới.

3. Bổ sung dữ liệu domain mới (Restaurant FAQs)

- Thêm bộ FAQ nhà hàng lớn, giúp tăng độ phủ cho truy vấn khó và truy vấn nghiệp vụ thực tế.
- Tạo nền tảng để benchmark đo đúng chất lượng retrieval trên domain GSM.

### 2.2. Liên hệ với module phức tạp (Async, Multi-Judge, Metrics)

- **Metrics (Hit Rate/MRR):** deterministic chunk ID giúp mapping `expected_retrieval_ids` ổn định, từ đó tính Hit Rate/MRR đáng tin cậy.
- **Multi-Judge:** chunk sạch theo section giúp đầu ra agent bám đúng context hơn, giảm sai lệch chấm điểm judge.
- **Async Runner:** ingest chuẩn hóa giúp batch benchmark chạy song song mà vẫn giữ tính nhất quán dữ liệu đầu vào.

Kết luận: đóng góp chính nằm ở **hạ tầng dữ liệu và retrieval foundation**, là điều kiện cần để các module phức tạp hoạt động đúng.

---

## 3. Technical Depth

### 3.1. MRR (Mean Reciprocal Rank)

- Ý nghĩa: đo vị trí xuất hiện của tài liệu đúng đầu tiên trong danh sách truy xuất.
- Công thức: `MRR = 1/rank` với `rank` là vị trí tài liệu đúng đầu tiên (1-indexed), không tìm thấy thì bằng 0.
- Tác dụng: phản ánh retrieval “đúng và sớm”, quan trọng cho RAG vì context đầu danh sách ảnh hưởng mạnh đến câu trả lời.

### 3.2. Cohen's Kappa

- Ý nghĩa: đo mức đồng thuận giữa 2 judge sau khi đã loại trừ phần trùng nhau do ngẫu nhiên.
- Trực giác:
  - `kappa = 1`: đồng thuận hoàn toàn.
  - `kappa = 0`: đồng thuận chỉ ở mức ngẫu nhiên.
  - `kappa < 0`: bất đồng mạnh.
- Vai trò trong lab: dùng để kiểm tra độ tin cậy của hệ chấm nhiều model, tránh phụ thuộc một judge.

### 3.3. Position Bias

- Định nghĩa: judge có xu hướng ưu tiên câu trả lời đứng vị trí A/B thay vì chất lượng thật.
- Cách kiểm tra: đảo thứ tự 2 câu trả lời và so sánh điểm.
- Nếu điểm đổi đáng kể khi đảo vị trí -> có bias, cần hiệu chỉnh prompt/judge policy.

### 3.4. Trade-off Chi phí vs Chất lượng

- Embedding model lớn hơn -> thường tăng chất lượng retrieval nhưng tăng chi phí và thời gian ingest.
- Chunk nhỏ -> tăng recall nhưng có thể giảm precision, số vector nhiều hơn làm tốn tài nguyên.
- Re-rank hoặc multi-judge -> tăng độ tin cậy nhưng tăng latency/cost.
- Cân bằng thực tế: chọn chunking theo section + model multilingual vừa phải để đạt chất lượng tốt trong ngân sách lab.

---

## 4. Problem Solving

### 4.1. Vấn đề 1: Import path khi chạy script từ nhiều vị trí

- Hiện tượng: script dễ lỗi import khi chạy từ thư mục khác.
- Cách xử lý: resolve project root bằng `Path(__file__).resolve().parent.parent` và thêm vào `sys.path`.
- Kết quả: `data/ingest.py` chạy ổn định, giảm lỗi môi trường khi team chạy chung.

### 4.2. Vấn đề 2: Dữ liệu markdown dài, nhiều mục FAQ

- Hiện tượng: chunk thô dễ mất ngữ nghĩa hoặc quá dài.
- Cách xử lý: split theo header cấp 2 (`##`) để giữ semantics theo câu hỏi/mục nghiệp vụ.
- Kết quả: retrieval bám context chính xác hơn, tiện debug theo section title.

### 4.3. Vấn đề 3: Re-ingest nhiều lần gây dữ liệu cũ lẫn dữ liệu mới

- Hiện tượng: chạy lại pipeline làm collection bị trùng/khó kiểm soát.
- Cách xử lý: xóa collection cũ trước khi tạo mới (idempotent run).
- Kết quả: bảo toàn tính lặp lại của benchmark và nhất quán số lượng chunk.
