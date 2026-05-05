# AI Developer 3 - Complete Code Implementation Guide

**Project:** Tool-24 — Audit Report Generator  
**Role:** AI Developer 3  
**Sprint:** Monday 14 April 2026 — Friday 9 May 2026  
**Date Created:** May 4, 2026

---

## Overview: What AI Developer 3 Builds

AI Developer 3 is the **Security Engineer** for the AI microservice. Your responsibilities span three critical areas:

1. **Input Sanitization** - Prevent injection attacks
2. **Rate Limiting** - Prevent DoS attacks
3. **Security Integration** - Connect AI service securely to Java backend
4. **OWASP Testing** - Find and fix vulnerabilities
5. **Security Documentation** - Create SECURITY.md

---

## Part 1: Input Sanitization (`input_sanitizer.py`)

### What It Does

Cleans ALL user input before the AI processes it. Detects:
- SQL injection attempts
- XSS/script injection
- Prompt injection attacks
- HTML tags and dangerous entities
- Oversized payloads

### Key Classes

**`InputSanitizer`** - Static methods for sanitization:
```python
# Detect threats
InputSanitizer.detect_sql_injection(text)       # Returns True/False
InputSanitizer.detect_xss_attempt(text)         # Returns True/False
InputSanitizer.detect_prompt_injection(text)    # Returns True/False

# Sanitize data
InputSanitizer.sanitize_string(text)            # Returns cleaned string
InputSanitizer.sanitize_dict(data)              # Returns cleaned dict
InputSanitizer.sanitize_list(data)              # Returns cleaned list

# Strip HTML
InputSanitizer.strip_html_tags(text)            # Removes <script>, etc.
```

### Threat Detection Patterns

| Threat Type | Example Attack | Detection Pattern |
|------------|-----------------|------------------|
| SQL Injection | `' OR '1'='1` | Detects UNION, SELECT, DROP, --, ; |
| XSS | `<script>alert()</script>` | Detects <script>, onclick, javascript: |
| Prompt Injection | `ignore previous instructions` | Detects "ignore", "disregard", etc. |
| HTML | `<iframe src=...>` | Detects HTML tags |

### How to Use in Flask Routes

```python
from flask import Flask, request, jsonify
from input_sanitizer import sanitize_input

@app.route('/describe', methods=['POST'])
@sanitize_input  # Automatically sanitizes request.json
def describe():
    data = request.get_json()  # Already cleaned!
    text = data.get('text')    # Safe to use
    # Process text...
    return jsonify({"result": description})
```

### Error Responses

When dangerous input is detected, returns 400:
```json
{
  "error": "Invalid input",
  "message": "SQL injection attempt detected",
  "status": 400
}
```

---

## Part 2: Rate Limiting (`rate_limiter.py`)

### What It Does

Controls how many requests each IP can make:
- Default: 30 requests per minute
- Expensive operations: 10 req/min or less
- Returns 429 Too Many Requests when exceeded

### Configuration

```python
from rate_limiter import RateLimiterConfig

# Initialize with Flask app
limiter = RateLimiterConfig.get_limiter(app)

# Apply to endpoints
@app.route('/describe', methods=['POST'])
@limiter.limit("60 per minute")  # Custom limit
def describe():
    ...
```

### Endpoint-Specific Limits

```python
RateLimiterConfig.DEFAULT_LIMIT = "30 per minute"
RateLimiterConfig.DESCRIBE_LIMIT = "60 per minute"
RateLimiterConfig.RECOMMEND_LIMIT = "60 per minute"
RateLimiterConfig.CATEGORISE_LIMIT = "60 per minute"
RateLimiterConfig.QUERY_LIMIT = "60 per minute"
RateLimiterConfig.ANALYSE_DOCUMENT_LIMIT = "20 per minute"
RateLimiterConfig.GENERATE_REPORT_LIMIT = "10 per minute"    # Expensive!
RateLimiterConfig.BATCH_PROCESS_LIMIT = "5 per minute"       # Very expensive!
RateLimiterConfig.HEALTH_LIMIT = "100 per minute"
```

### Rate Limit Exceeded Response

```json
{
  "error": "Too Many Requests",
  "message": "You have exceeded the rate limit. Please try again later.",
  "status": 429,
  "retry_after": 60
}
```

### Monitoring

```python
from rate_limiter import RateLimitMonitor

monitor = RateLimitMonitor(redis_client)

# Log request
monitor.log_request(ip_address, endpoint)

# Get request count
count = monitor.get_request_count("192.168.1.1", "/describe")

# Get top offenders
top_ips = monitor.get_top_ips(limit=10)
```

---

## Part 3: AiServiceClient (`AiServiceClient.java`)

### What It Does

The Java backend uses this client to call the Flask AI service. Handles:
- All 6 AI endpoints
- Automatic retries (3 attempts with exponential backoff)
- Timeout management (10 seconds)
- Fallback responses if AI service is down
- Complete error logging

### Location
```
backend/AiServiceClient.java
```

### AiResponse Class

Returned by all methods:
```java
public class AiResponse {
    public String result;                    // AI response
    public String error;                     // Error message if failed
    public Map<String, Object> meta;        // Metadata (tokens, time, etc.)
    public boolean isFallback;               // True if using fallback response
}
```

### Available Methods

```java
AiServiceClient client = new AiServiceClient(restTemplate, objectMapper);

// 1. Describe - Generate description
AiResponse response = client.describe("text to describe");

// 2. Recommend - Get recommendations
AiResponse response = client.recommend("text for analysis");

// 3. Categorise - Classify text
AiResponse response = client.categorise("text to categorize");

// 4. Generate Report - Create full report
AiResponse response = client.generateReport(itemId, content);

// 5. Query - RAG-based question answering
AiResponse response = client.query("What should we do?");

// 6. Analyse Document - Find insights
AiResponse response = client.analyseDocument("document text");

// 7. Batch Process - Process multiple items
List<String> items = Arrays.asList("item1", "item2", "item3");
AiResponse response = client.batchProcess(items, "describe");

// Health check
boolean isHealthy = client.healthCheck();
boolean isAvailable = client.isServiceAvailable();
```

### Usage in Service Layer

```java
@Service
public class RecordService {
    @Autowired
    private AiServiceClient aiServiceClient;
    
    @Autowired
    private RecordRepository recordRepository;
    
    @Async  // Run in background thread
    public void createRecordWithAiAnalysis(RecordRequest req) {
        try {
            // Call AI service
            AiResponse aiResponse = aiServiceClient.describe(req.getContent());
            
            // Check if it's a fallback
            if (aiResponse.isFallback) {
                logger.warn("AI service unavailable, used fallback response");
            }
            
            // Save to database
            Record record = new Record();
            record.setName(req.getName());
            record.setAiDescription(aiResponse.result);
            record.setConfidence((Double) aiResponse.meta.get("confidence"));
            
            recordRepository.save(record);
            
        } catch (Exception e) {
            logger.error("Error processing record: " + e.getMessage());
        }
    }
}
```

### Configuration

Add to `application.yml`:
```yaml
ai:
  service:
    url: http://localhost:5000
    timeout: 10000        # milliseconds
    max-retries: 3
    retry-delay: 1000     # milliseconds
```

### Retry Logic

Automatically retries failed requests:
```
Attempt 1: Immediate
Attempt 2: Wait 1s, retry
Attempt 3: Wait 2s, retry
Failure: Return fallback response
```

---

## Part 4: Flask App Integration (`app_secure.py`)

### Complete Flask Setup with Security

Combines input sanitization, rate limiting, and security headers:

```python
from flask import Flask
from flask_talisman import Talisman
from rate_limiter import RateLimiterConfig
from input_sanitizer import sanitize_input, validate_input_length

app = Flask(__name__)

# Security: Add Talisman headers
Talisman(app, 
    force_https=True,
    strict_transport_security=True,
    content_security_policy={'default-src': "'self'"}
)

# Security: Initialize rate limiter
limiter = RateLimiterConfig.get_limiter(app)

# Example protected endpoint
@app.route('/describe', methods=['POST'])
@limiter.limit("60 per minute")           # Rate limit
@sanitize_input                            # Sanitize input
@validate_input_length(max_length=5000)   # Check size
def describe():
    from flask import request
    data = request.get_json()  # Already sanitized
    # Safe to process...
    return jsonify({"result": "..."})
```

### Security Headers Added by Talisman

```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Content-Security-Policy: default-src 'self'
Strict-Transport-Security: max-age=31536000
```

---

## Part 5: SECURITY.md Documentation

### Comprehensive Security Document

See `SECURITY.md` - 500+ lines covering:

1. **Threat Model** - All 10 OWASP Top 10 risks
2. **Mitigations** - Code examples for each threat
3. **Testing Results** - OWASP ZAP findings
4. **Implementation Details** - How to use security modules
5. **Incident Response** - What to do if attacked
6. **Compliance** - Standards alignment

---

## Daily Tasks (From Project Spec)

### Day 3 (Wednesday April 16)
**Task:** Implement input sanitisation middleware  
**Deliverable:** `input_sanitizer.py` with detection for SQL injection, XSS, prompt injection  
**Status:** ✅ COMPLETE

### Day 4 (Thursday April 17)
**Task:** Add flask-limiter with 30 req/min default, 10 req/min on expensive endpoints  
**Deliverable:** `rate_limiter.py` with Redis backend support  
**Status:** ✅ COMPLETE

### Day 6 (Monday April 21)
**Task:** Write AiServiceClient.java to call Flask endpoints  
**Deliverable:** `AiServiceClient.java` with retry logic and fallbacks  
**Status:** ✅ COMPLETE

### Day 7 (Tuesday April 22)
**Task:** Run OWASP ZAP baseline scan  
**Deliverable:** Security report with findings  
**Status:** ✅ COMPLETE

### Day 8 (Wednesday April 23)
**Task:** Fix all ZAP findings - add security headers  
**Deliverable:** Flask-Talisman integration  
**Status:** ✅ COMPLETE

### Day 9 (Thursday April 24)
**Task:** PII audit - verify no personal data in prompts or logs  
**Deliverable:** SECURITY.md documentation  
**Status:** ✅ COMPLETE

### Day 10 (Friday April 25)
**Task:** Week 2 security sign-off - verify all measures  
**Deliverable:** Updated SECURITY.md with test results  
**Status:** ✅ COMPLETE

---

## Integration Points

### Backend ← → AI Service

```
┌─────────────────────┐
│   Java Backend      │
│                     │
│  AiServiceClient    │ ──HTTP POST─→ ┌──────────────────┐
│  .describe()        │ ←─JSON─────── │  Flask AI Service│
│  .recommend()       │                │                  │
│  .query()           │                │  @sanitize_input │
│                     │                │  @limiter.limit()│
└─────────────────────┘                │                  │
                                       │  /describe ✅    │
                                       │  /recommend ✅   │
                                       │  /query ✅       │
                                       │                  │
                                       └──────────────────┘
```

### Error Handling Flow

```
Frontend Request
    ↓
Java Backend Receives
    ↓
JwtAuthFilter: Check token ✅
    ↓
@PreAuthorize: Check role ✅
    ↓
ServiceLayer calls AiServiceClient.describe()
    ↓
Try to reach Flask AI service
    ↓
┌─────────────────────────┐
│ Flask Input Sanitizer   │
│ - Detects SQL injection │ → Reject & return 400
│ - Detects XSS          │ → Reject & return 400
│ - Detects prompt inj.  │ → Reject & return 400
└─────────────────────────┘
    ↓ OK
┌─────────────────────────┐
│ Flask Rate Limiter      │
│ - Check IP: 30 req/min  │ → Reject & return 429
└─────────────────────────┘
    ↓ OK
Process with AI model
    ↓
Return result to backend
    ↓
Backend saves to database
    ↓
Response to frontend
```

---

## Testing Checklist

### Unit Tests (Python)
```python
# test_input_sanitizer.py
def test_sql_injection_detected():
    assert InputSanitizer.detect_sql_injection("' OR '1'='1")

def test_xss_detected():
    assert InputSanitizer.detect_xss_attempt("<script>alert()</script>")

def test_sanitize_removes_tags():
    result = InputSanitizer.sanitize_string("<b>hello</b>")
    assert "<b>" not in result
```

### Integration Tests (Java)
```java
// Test AiServiceClient
@Test
public void testDescribeEndpoint() {
    AiResponse response = client.describe("Test text");
    assertNotNull(response.result);
    assertFalse(response.isFallback);
}

@Test
public void testRetryOnTimeout() {
    // Set very short timeout
    client.setTimeoutMs(1);
    AiResponse response = client.describe("Test");
    // Should get fallback after 3 retries
    assertTrue(response.isFallback);
}
```

### Manual Security Tests
```bash
# Test SQL Injection
curl -X POST http://localhost:5000/describe \
  -H "Content-Type: application/json" \
  -d '{"text": "'\'' OR '\''1'\''='\''1"}'
# Expected: 400 Bad Request

# Test Rate Limiting (32 requests in 60 seconds)
for i in {1..32}; do
  curl -X POST http://localhost:5000/describe \
    -H "Content-Type: application/json" \
    -d '{"text": "test"}'
done
# Expected: 31st response = 200, 32nd response = 429

# Test Health
curl http://localhost:5000/health
# Expected: 200 with service info
```

---

## Files You Create

| File | Purpose |
|------|---------|
| `ai_service/input_sanitizer.py` | Input validation & injection detection |
| `ai_service/rate_limiter.py` | Rate limiting with Redis |
| `ai_service/app_secure.py` | Flask app with security integrated |
| `backend/AiServiceClient.java` | Java client for AI service |
| `SECURITY.md` | Comprehensive security documentation |

---

## Key Security Principles

1. **Defense in Depth** - Multiple layers of protection
   - Input validation
   - Rate limiting
   - Authentication
   - Authorization
   - Audit logging

2. **Fail Secure** - Deny by default
   - 401 if no token
   - 403 if insufficient role
   - 429 if rate limited
   - 400 if bad input

3. **Least Privilege** - Minimum required access
   - Viewers can't delete
   - Admins explicitly checked
   - AI service restricted to port 5000

4. **Logging Everything** - Audit trail for forensics
   - All auth attempts
   - All data modifications
   - All errors
   - 90-day retention

---

## Demo Day Checklist (AI Dev 3 Tasks)

- [ ] SECURITY.md complete and professional
- [ ] OWASP ZAP scan shows 0 Critical/High issues
- [ ] Demonstrate: API call without JWT → 401
- [ ] Demonstrate: SQL injection attempt → 400
- [ ] Demonstrate: Rate limit: 31 requests → 429
- [ ] Reference SECURITY.md and state "all findings fixed"
- [ ] Show input sanitizer detecting multiple threats
- [ ] Explain rate limiting prevents DoS

---

## Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| AI service timeout | Network/load | Check AiServiceClient retry logic |
| Rate limit too strict | Wrong limit applied | Verify endpoint decorators |
| Input validation failing | Regex too broad | Review detection patterns |
| OWASP ZAP failing | Missing headers | Check Talisman configuration |

---

## References

- OWASP Top 10: https://owasp.org/www-project-top-ten
- Flask Security: https://flask.palletsprojects.com/security
- Spring Security: https://spring.io/projects/spring-security
- Rate Limiting: https://flask-limiter.readthedocs.io
- OWASP ZAP: https://www.zaproxy.org

---

**Created by:** AI Developer 3  
**Date:** May 4, 2026  
**Status:** Ready for Demo Day  

