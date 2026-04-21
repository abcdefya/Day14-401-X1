# Báo cáo Cá nhân — Đỗ Thế Anh (2A202600040)

## 1. Đóng góp Engineering (Git Commits)

| Commit | Nội dung | Files thay đổi |
|--------|----------|---------------|
| `8600cd9` | **Refactor main.py** — viết lại toàn bộ benchmark orchestrator: async V1+V2 concurrent, `build_summary()`, `release_gate()`, báo cáo regression | main.py (+229/-71) |
| `20991a5` | **Golden Dataset** — tạo `data/golden_set.jsonl` với 146 test cases (50+ dùng để benchmark) | golden_set.jsonl (+146) |
| `16e80b4` | **Summary & Reports** — sinh `reports/summary.json`, `reports/benchmark_results.json`, hoàn thiện `analysis/failure_analysis.md` | 7 files (+3384) |
| `ccbac46` | **Thêm dữ liệu** — bổ sung `data/GSM/XanhSM - electric_car_driver FAQs.md` | +56 lines |
| `4621165` | **Config** — tạo `.env.example`, cập nhật `.gitignore` | 2 files |
| `29707dd` | **README** — viết lại README chi tiết hướng dẫn sử dụng hệ thống | README.md (+152) |

**Module phức tạp tôi phụ trách chính:** `main.py` — Benchmark Orchestrator

---

## 2. Giải thích Kỹ thuật

### Hit Rate & MRR
- **Hit Rate**: tỷ lệ test cases có ít nhất 1 chunk đúng trong top-k kết quả retrieval. Hệ thống đạt **0.90** — nghĩa là 90% câu hỏi retrieve được tài liệu liên quan.
- **MRR (Mean Reciprocal Rank)**: trung bình của `1/rank` của chunk đúng đầu tiên. MRR = **0.80** cho thấy chunk đúng thường xuất hiện ở vị trí 1–2, ảnh hưởng trực tiếp đến chất lượng câu trả lời.
- **Mối liên hệ**: Hit Rate cao → LLM có context đúng → Answer Quality cao. MRR cao → chunk đúng ở vị trí đầu → ít bị noise từ chunks không liên quan.

### Multi-Judge Consensus & Agreement Rate
- Hệ thống dùng **2 model judge** (Groq `llama-3.3-70b` + `gpt-oss-120b`) để tránh bias từ một model đơn.
- **Agreement Rate** = tỷ lệ cases mà `|score_A - score_B| ≤ 1`. V2 đạt **0.68**, tăng từ 0.64 của V1.
- **Conflict resolution**: khi 2 judge bất đồng (|Δ| > 1), vẫn lấy trung bình nhưng flag `conflict=True`. V2 giảm conflicts từ 18 → 16 cases.
- **Cohen's Kappa** đo agreement sau khi trừ đi xác suất đồng ý ngẫu nhiên — chỉ số chặt chẽ hơn agreement rate thuần túy.
- **Position Bias**: các LLM judge có xu hướng cho điểm cao hơn nếu câu trả lời dài hoặc xuất hiện đầu tiên. Hệ thống dùng 2 model khác nhau để giảm thiểu bias này.

### Trade-off Chi phí vs Chất lượng
- V1 dùng 52,757 tokens (~$0.0528), V2 tối ưu còn 47,912 tokens (~$0.0479) nhờ system prompt ngắn gọn hơn.
- Avg latency giảm từ 213s → 162s nhờ async batch processing (batch_size=20).
- **Release Gate** tự động APPROVE/BLOCK dựa trên ngưỡng: avg_score ≥ 3.0, hit_rate ≥ 0.6, agreement ≥ 0.6, regression delta ≥ -0.2.

---

## 3. Problem Solving

**Vấn đề:** main.py ban đầu dùng `ExpertEvaluator` và `MultiModelJudge` giả lập (mock), không tính metrics thực.

**Giải pháp:** Refactor hoàn toàn — kết nối trực tiếp với `LLMJudge` thật, tính `hit_rate`/`mrr`/`agreement_rate` từ kết quả thực tế, chạy V1 và V2 **concurrent** bằng `asyncio.gather()` để giảm thời gian chạy 50 cases xuống dưới 3 phút.

**Vấn đề 2:** Golden set ban đầu thiếu — không có dữ liệu xe điện (electric car driver FAQs).

**Giải pháp:** Bổ sung `XanhSM - electric_car_driver FAQs.md` và tích hợp vào golden set để tăng độ phủ test cases.

---

## 4. Kết quả Benchmark

| Metric | V1 | V2 | Status |
|--------|----|----|--------|
| Avg Judge Score | 3.600 | 3.530 | ▼ -0.07 (within threshold) |
| Hit Rate | 0.900 | 0.900 | = |
| MRR | 0.800 | 0.800 | = |
| Agreement Rate | 0.640 | 0.680 | ▲ +0.04 |
| Avg Latency | 213s | 162s | ▲ -51s |

**Release Gate: APPROVE** — tất cả ngưỡng chất lượng đều đạt.
