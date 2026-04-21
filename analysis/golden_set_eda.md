# EDA Report: golden_set.jsonl

- Input file: `C:\Users\minhk\lab14\Day14-401-X1\data\golden_set.jsonl`
- Generated at (local): 21/04/2026, 15:51:46
- Total non-empty lines: 146
- Parsed JSON rows: 146
- Parse error lines: 0

## Schema Summary
### Top-level keys (presence count)
- `expected_answer`: 146
- `expected_retrieval_ids`: 146
- `metadata`: 146
- `question`: 146

### metadata keys (presence count)
- `difficulty`: 146
- `type`: 146
- `source_chunk`: 136

### Missing/null counts
- `question`: 0
- `expected_answer`: 0
- `expected_retrieval_ids`: 0
- `metadata`: 0
- `expected_retrieval_ids` present but not array: 0
- `metadata` present but not object: 0

## Label Distributions
### metadata.type
- `procedure`: 106
- `fact_check`: 23
- `multi_fact`: 10
- `edge_case`: 1
- `goal_hijacking`: 1
- `multi_hop`: 1
- `out_of_context`: 1
- `prompt_injection`: 1
- `safety`: 1
- `time_sensitive`: 1

### metadata.difficulty
- `medium`: 124
- `easy`: 18
- `adversarial`: 2
- `hard`: 2

### Top source chunks
- `car_driver_faq_1.1`: 1
- `car_driver_faq_1.2`: 1
- `car_driver_faq_1.3`: 1
- `car_driver_faq_1.4`: 1
- `car_driver_faq_2.1`: 1
- `car_driver_faq_2.2`: 1
- `car_driver_faq_2.3`: 1
- `car_driver_faq_3.1`: 1
- `car_driver_faq_3.2`: 1
- `car_driver_faq_3.3`: 1
- `car_driver_faq_intro`: 1
- `motor_driver_faq_1.1`: 1
- `motor_driver_faq_1.10`: 1
- `motor_driver_faq_1.11`: 1
- `motor_driver_faq_1.12`: 1
- `motor_driver_faq_1.13`: 1
- `motor_driver_faq_1.14`: 1
- `motor_driver_faq_1.15`: 1
- `motor_driver_faq_1.16`: 1
- `motor_driver_faq_1.2`: 1

### Top expected retrieval IDs
- `car_driver_faq_1.1`: 2
- `car_driver_faq_1.3`: 2
- `car_driver_faq_1.4`: 2
- `restaurant_faq_1.2`: 2
- `user_faq_1.2`: 2
- `user_faq_1.4`: 2
- `user_faq_1.7`: 2
- `car_driver_faq_1.2`: 1
- `car_driver_faq_2.1`: 1
- `car_driver_faq_2.2`: 1
- `car_driver_faq_2.3`: 1
- `car_driver_faq_3.1`: 1
- `car_driver_faq_3.2`: 1
- `car_driver_faq_3.3`: 1
- `car_driver_faq_intro`: 1
- `motor_driver_faq_1.1`: 1
- `motor_driver_faq_1.10`: 1
- `motor_driver_faq_1.11`: 1
- `motor_driver_faq_1.12`: 1
- `motor_driver_faq_1.13`: 1

## Text Length Stats
### question length (chars)
- min: 34
- p25: 71
- median: 105.5
- p75: 157
- p90: 204
- max: 818
- mean: 124.10

### expected_answer length (chars)
- min: 4
- p25: 113
- median: 169.5
- p75: 233
- p90: 376
- max: 784
- mean: 193.01

### expected_retrieval_ids count per row
- min: 0
- p25: 1
- median: 1
- p75: 1
- p90: 1
- max: 2
- mean: 0.98

## Quality Checks
- Unique questions: 146/146 (100.00%)
- Unique answers: 146/146 (100.00%)
- Duplicate question groups: 0
- Duplicate question extra rows: 0
- Duplicate answer groups: 0
- Duplicate answer extra rows: 0
- Rows where `metadata.source_chunk` appears in `expected_retrieval_ids`: 136/146 (93.15%)
- Mojibake heuristic hits in question: 0/146 (0.00%)
- Mojibake heuristic hits in expected_answer: 0/146 (0.00%)

## Duplicate Samples
### Top duplicate questions (up to 10)
- None

### Top duplicate answers (up to 10)
- None

## Parse Errors
- None
