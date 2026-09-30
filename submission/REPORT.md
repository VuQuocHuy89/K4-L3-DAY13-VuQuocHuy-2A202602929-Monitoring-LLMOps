# Báo cáo cá nhân — K4-L3B Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên:** Vũ Quốc Huy
- **MSSV:** 2A202602929
- **Lớp:** K4-L3B
- **Repository URL:** https://github.com/VuQuocHuy89/K4-L3-DAY13-VuQuocHuy-2A202602929-Monitoring-LLMOps
- **Commit SHA cuối:** Xem commit mới nhất của repository; sẽ cập nhật SHA này trên VLearn sau khi push.
- **Challenge ID:** `day13-k4-l3b-monitoring-llmops-v1` (`rag_slow`, K4-L3B)
- **Tên project Langfuse cá nhân:** `day13-k4-l3b-2A202602929`

## 2. Evidence index

Điền đúng đường dẫn tới evidence thực tế. Có thể đổi tên hoặc dùng nhiều ảnh nếu cần.

| Evidence | Đường dẫn |
|---|---|
| Pytest cuối | `evidence/01-pytest.txt` |
| Log validator | `evidence/02-log-validator.txt` |
| Dashboard validator | `evidence/03-dashboard-validator.txt` |
| Structured log | `evidence/04-structured-log.png` |
| PII redaction | `evidence/05-pii-redaction.png` |
| Trace list | `evidence/06-trace-list.png` |
| Trace waterfall | `evidence/07-trace-waterfall.png` |
| Trace metadata | `evidence/08-trace-metadata.png` |
| Prompt versions | `evidence/09-prompt-versions.png` |
| Prompt rollback | `evidence/10-prompt-rollback-before.png`, `evidence/10-prompt-rollback-after.png` |
| Dashboard runtime | `evidence/11-dashboard-overview.png` |
| Incident metric | `evidence/12-incident-metric.png` |
| Incident log | `evidence/13-incident-log.png` |
| Incident trace | `evidence/14-incident-trace.png` |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | Không ghi nhận | 100/100; 13 dòng, 0 thiếu field/enrichment, 0 PII hit | 7 correlation ID duy nhất |
| `validate_dashboard.py` | Không ghi nhận | HỢP LỆ: 6/6 panel | Contract có đủ sáu panel bắt buộc |
| `pytest` | Không ghi nhận | 25 passed trên code repo L3B | Dependencies dùng virtualenv L3A có sẵn; test chạy tại worktree L3B |
| Số traces hợp lệ | Không ghi nhận | 5 trace challenge chính thức | 15 observations; mỗi trace có root, retrieval và generation |
| Số PII leak | Không ghi nhận | 0 trong logs; raw trace input/output không capture | Dữ liệu challenge synthetic; generation I/O được scrub |
| Latency P95 / TTFT P95 | Không ghi nhận | 3816 ms / 51 ms | 5 request; challenge threshold 2000 ms; 5/5 vượt ngưỡng |
| Retrieval success rate | Không ghi nhận | 100% (5/5) | Retrieval hoàn tất; mỗi span mất 2.5 giây khi rag_slow bật |

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:** Middleware nhận `x-request-id` đúng mẫu `req-<8-hex>` hoặc tự sinh ID; bind vào structlog context, trả lại qua `x-request-id` và ghi cùng ID vào trace metadata.
- **Các metadata được ghi vào structured log:** `user_id_hash`, `session_id`, `feature`, `model`, `env`, `correlation_id` cùng các trường latency/token/cost/quality khi hoàn tất request.
- **Cách bảo đảm PII được scrub trước khi ghi:** Processor đệ quy scrub mọi chuỗi trong event trước JSON renderer và JSONL file writer; user ID được hash.
- **Cách kiểm chứng kết quả:** Pytest 25 passed trên code L3B; log validator 100/100 trên 13 dòng challenge, không thiếu field/enrichment và không phát hiện PII; dashboard validator đạt 6/6.

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:** Đối chiếu project Langfuse L3B trong cấu hình; 5 trace chính thức được truy vấn qua Observations API v2 và từng correlation ID khớp local logs.
- **Cấu trúc root/retrieval/generation observations:** Root `lab-agent-run` (`AGENT`) có child `retrieval` (`RETRIEVER`) và `llm-call` (`GENERATION`); generation ghi model, prompt version, token usage và cost.
- **Cách nối trace với log:** `correlation_id` có trong request log và metadata của cả ba observations; 5/5 challenge trace khớp.
- **Prompt name:** `day13-chat`
- **Version/label baseline:** v1 / `baseline`
- **Version/label candidate:** v2 / `candidate`
- **Trace ID của mỗi version:** Cùng một input: baseline v1 (`baseline`) — `e456c0e91d0eba0f0eae4873fb95bd58`; candidate v2 (`candidate`) — `b4bf6a7bac7acd3358ae16e1728f0e28`; cả hai trace có `prompt_source=langfuse`. Batch challenge chạy với production v1; trace IDs: `44d1ecedf5ed532043eac2b7938f5dc4`, `22371b8ff9d4f941b51db7879e31c478`, `483fc7ed29a2d8184ea52224c61a803b`, `852696e16581c50b229d8c7eebfa80b2`, `de45fa4e0ad801e49ba3dc663fe92931`.
- **Cách promote và rollback `production`:** Đã chuyển production sang v2 để ghi nhận trạng thái trước, sau đó rollback về v1; baseline vẫn v1 và candidate vẫn v2. Xem ảnh before/after ở `evidence/10-prompt-rollback-before.png` và `evidence/10-prompt-rollback-after.png`. Batch challenge vẫn dùng production v1.

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:** Dashboard đọc `data/logs.jsonl`, có latency (P50/P95/P99/TTFT), traffic, errors/retrieval success, cost, tokens và quality; validator đạt 6/6.
- **SLO và lý do chọn:** 99.5% request hoàn tất trong ≤3000 ms trong cửa sổ 28 ngày; đây là mục tiêu cho fast successful requests.
- **Cách tính error budget:** 0.5% phần request lỗi/vượt 3000 ms, tương đương tối đa 50 request xấu trên 10,000 request trong 28 ngày.
- **Ba alert và runbook tương ứng:** `HighRequestLatency` (>3000 ms P95/5m), `ElevatedRequestErrors` (>2%/5m), `LowRetrievalSuccess` (<90%/5m); runbook lần lượt ở `docs/alerts.md#alert-1`, `#alert-2`, `#alert-3`.

> Ví dụ cách viết error budget: "SLO 99.5% trong 28 ngày nghĩa là error budget 0.5%. Nếu workload có 10,000 request thì tối đa 50 request được phép lỗi hoặc chậm hơn ngưỡng SLO."

## 7. Điều tra challenge

- **Challenge ID:** `day13-k4-l3b-monitoring-llmops-v1` (`rag_slow`, K4-L3B)
- **Khoảng thời gian điều tra:** 2026-09-30 04:08:14–04:08:29 UTC; 5 request trong metric window 60 phút.
- **Triệu chứng từ metrics:** Latency P95 3816 ms vượt challenge threshold 2000 ms (5/5 request); error rate 0%, retrieval success 100%, TTFT P95 51 ms.
- **Log line và correlation ID liên quan:** `response_sent` có `latency_ms=3816`, `tool_success=true`; correlation ID `req-964f66f0`. Xem `evidence/13-incident-log.png`.
- **Trace ID và span gây ảnh hưởng:** `44d1ecedf5ed532043eac2b7938f5dc4`; `retrieval` (`RETRIEVER`) kéo dài 2500 ms; correlation ID trùng log.
- **Root cause:** Challenge `rag_slow` làm mock retriever sleep 2.5 giây mỗi lần; retrieval span xác nhận đúng độ trễ.
- **Fix action:** Tắt incident qua `/incidents/rag_slow/disable`; endpoint trả về `rag_slow=false` và các incident flag khác cũng false.
- **Preventive measure:** Giữ alert HighRequestLatency P95 >3000 ms và runbook kiểm tra retrieval dependency; challenge threshold 2000 ms giúp phát hiện chậm trước khi ảnh hưởng SLO.

> Gợi ý cách viết ngắn, không thay cho evidence thực tế: "Metric cho thấy `[latency/error/cost/quality]` bất thường trong `[khoảng thời gian]`. Log line `[event]` có `correlation_id=[...]` đại diện cho request bị ảnh hưởng. Trace cùng `correlation_id` cho thấy span `[retrieval/generation/prompt/tool]` có dấu hiệu `[chậm/lỗi/token tăng]`. Root cause là `[nguyên nhân suy ra từ evidence]`. Fix action là `[hành động khôi phục]`; preventive measure là `[alert/runbook/test/guardrail để ngăn tái diễn]`."

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:** Scrub đệ quy toàn event trước mọi output để PII không lọt qua trường lồng nhau hoặc sink khác.
- **Một lỗi/blocker đã gặp:** Lượt challenge đầu tiên báo timeout khi export trace; chạy lại trên log sạch và giữ API hoạt động đến khi 5 root trace xuất hiện trong Langfuse.
- **Cách tìm nguyên nhân và xử lý:** Metrics cho thấy P95 vượt 2000 ms; log chọn `req-964f66f0`; trace chỉ ra retrieval span 2500 ms; tắt `rag_slow` và xác nhận trạng thái false.
- **Cách hiểu luồng Metrics → Logs → Traces:** Metrics xác định triệu chứng, correlation ID tìm request trong logs, trace cho biết span gây lỗi.
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:** Version gắn request với prompt đã chạy; usage/cost quan sát tiêu thụ; SLO giới hạn lỗi/chậm; rollback đưa production về prompt v1 đã kiểm chứng.
- **Điều quan trọng nhất đã học:** Có thể lần từ triệu chứng aggregate tới đúng request và span khi correlation ID được truyền xuyên suốt.
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:** Không còn phần kỹ thuật chưa hoàn thành; commit SHA cuối sẽ được cập nhật trên VLearn sau khi push. `config/challenge.json` và `.env` được giữ ngoài Git theo hướng dẫn.

## 9. Checklist trước khi nộp

- [x] Kết quả và evidence thuộc commit SHA cuối.
- [x] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [x] Incident evidence nối đúng metric → log → trace.
- [x] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret.
- [x] Repository chạy lại được theo README.
- [x] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [ ] URL repository và commit SHA cuối đã được cập nhật trên VLearn sau lần push này.
