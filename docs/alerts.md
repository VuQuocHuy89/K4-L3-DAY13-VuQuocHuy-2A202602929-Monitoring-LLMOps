# Template Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert mẫu để tham khảo

Ví dụ dưới đây minh họa mức độ cụ thể cần có. Học viên không cần copy nguyên, nhưng ba alert trong bài nộp nên rõ ràng tương tự: điều kiện là gì, kéo dài bao lâu, ảnh hưởng tới user ra sao và người trực cần kiểm tra gì trước.

- Tên: `HighLatencyP95`
- Severity: `warning`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: latency P95 của `response_sent.latency_ms`
- Điều kiện và thời gian duy trì: `p95(latency_ms) > 3000ms` trong 5 phút
- Ảnh hưởng tới người dùng: người dùng phải chờ lâu hơn trước khi nhận câu trả lời
- Ba bước kiểm tra đầu tiên:
  1. Mở dashboard latency để xác nhận P95/P99 và khoảng thời gian tăng.
  2. Lọc `data/logs.jsonl` trong khoảng đó, lấy một `correlation_id` có `latency_ms` cao.
  3. Mở trace cùng `correlation_id` trên Langfuse, so sánh các span chính để xác định bước nào bất thường.
- Mitigation tạm thời: dựa trên evidence thực tế để rollback prompt, khôi phục cấu hình liên quan, tắt practice scenario hoặc giảm tải khi demo.
- Owner: `student-<MSSV>`

## Alert 1

- Tên: HighRequestLatency
- Severity: warning
- Duration: 5m
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: P95 latency; fast successful request target 99.5% trong 28 ngày.
- Điều kiện và thời gian duy trì: `latency_p95_ms > 3000` liên tục 5 phút.
- Ảnh hưởng tới người dùng: người dùng chờ lâu hoặc request vượt ngưỡng SLO.
- Ba bước kiểm tra đầu tiên: (1) xem P50/P95/P99 và TTFT theo cùng time range; (2) lọc `response_sent` chậm trong `data/logs.jsonl`, ghi correlation ID; (3) mở trace tương ứng, so thời gian retrieval với generation.
- Mitigation tạm thời: nếu retrieval chậm, giảm tải hoặc tạm tắt truy vấn tốn thời gian; nếu generation chậm, giảm output token limit hoặc quay về prompt production ổn định. Theo dõi P95 sau mitigation.
- Owner: student-2A202602929

## Alert 2

- Tên: ElevatedRequestErrors
- Severity: critical
- Duration: 5m
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: tỷ lệ request hoàn tất thành công; lỗi tiêu thụ error budget.
- Điều kiện và thời gian duy trì: `error_rate_pct > 2` liên tục 5 phút.
- Ảnh hưởng tới người dùng: người dùng nhận lỗi thay vì câu trả lời.
- Ba bước kiểm tra đầu tiên: (1) đối chiếu error rate và error breakdown; (2) lọc `request_failed` theo time range và correlation ID; (3) mở trace để xác định span lỗi.
- Mitigation tạm thời: tắt feature/incident gây lỗi nếu xác định được, khôi phục cấu hình/prompt cuối ổn định, rồi chạy lại workload nhỏ để xác nhận tỷ lệ lỗi giảm.
- Owner: student-2A202602929

## Alert 3

- Tên: LowRetrievalSuccess
- Severity: critical
- Duration: 5m
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: retrieval success rate guardrail tối thiểu 90%.
- Điều kiện và thời gian duy trì: `retrieval_success_rate_pct < 90` liên tục 5 phút.
- Ảnh hưởng tới người dùng: câu trả lời có thể thiếu ngữ cảnh hoặc request thất bại.
- Ba bước kiểm tra đầu tiên: (1) xem retrieval success và error breakdown; (2) tìm log có `tool_name=retrieval` và `tool_success=false`; (3) mở trace cùng correlation ID, kiểm tra retrieval observation.
- Mitigation tạm thời: kiểm tra trạng thái retriever/vector store; nếu dependency không ổn định, dùng fallback đã được duyệt và xác nhận lỗi giảm trước khi đóng alert.
- Owner: student-2A202602929
