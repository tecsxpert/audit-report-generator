package com.internship.tool.config;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestTemplate;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.*;
import java.util.concurrent.TimeUnit;

/**
 * AI Service Client for Java Backend
 * AI Developer 3 Responsibility
 * 
 * Handles all communication with Flask AI microservice on port 5000
 * Includes retry logic, timeouts, and error handling
 */
@Component
public class AiServiceClient {
    
    private static final Logger logger = LoggerFactory.getLogger(AiServiceClient.class);
    
    @Value("${ai.service.url:http://localhost:5000}")
    private String aiServiceUrl;
    
    @Value("${ai.service.timeout:10000}")
    private int timeoutMs;
    
    @Value("${ai.service.max-retries:3}")
    private int maxRetries;
    
    @Value("${ai.service.retry-delay:1000}")
    private int retryDelayMs;
    
    private final RestTemplate restTemplate;
    private final ObjectMapper objectMapper;
    
    // Response wrapper class
    public static class AiResponse {
        public String result;
        public String error;
        public Map<String, Object> meta;
        public boolean isFallback;
        
        public AiResponse() {}
        
        public AiResponse(String result, Map<String, Object> meta) {
            this.result = result;
            this.meta = meta;
            this.isFallback = false;
        }
        
        public AiResponse(String error, boolean isFallback) {
            this.error = error;
            this.isFallback = isFallback;
        }
    }
    
    // Fallback responses
    private static final Map<String, String> FALLBACK_RESPONSES = Map.ofEntries(
        Map.entry("describe", "A professional audit document requiring careful review and analysis."),
        Map.entry("recommend", "[{\"action_type\": \"review\", \"description\": \"Review document carefully\", \"priority\": \"high\"}]"),
        Map.entry("categorise", "{\"category\": \"general\", \"confidence\": 0.5, \"reasoning\": \"Unable to categorize at this time\"}"),
        Map.entry("generate-report", "{\"title\": \"Audit Report\", \"executive_summary\": \"Report generation pending\", \"overview\": \"Document analysis in progress\", \"top_items\": [], \"recommendations\": []}"),
        Map.entry("query", "{\"answer\": \"Unable to answer at this time\", \"sources\": []}"),
        Map.entry("analyse-document", "[{\"insight\": \"Document analysis unavailable\", \"severity\": \"medium\"}]")
    );
    
    public AiServiceClient(RestTemplate restTemplate, ObjectMapper objectMapper) {
        this.restTemplate = restTemplate;
        this.objectMapper = objectMapper;
    }
    
    /**
     * Call /describe endpoint
     * 
     * @param text Input text to describe
     * @return AI-generated description or fallback
     */
    public AiResponse describe(String text) {
        Map<String, Object> payload = new HashMap<>();
        payload.put("text", text);
        
        return callEndpoint("/describe", payload, "describe");
    }
    
    /**
     * Call /recommend endpoint
     * 
     * @param text Input text for recommendations
     * @return Array of recommendations
     */
    public AiResponse recommend(String text) {
        Map<String, Object> payload = new HashMap<>();
        payload.put("text", text);
        
        return callEndpoint("/recommend", payload, "recommend");
    }
    
    /**
     * Call /categorise endpoint
     * 
     * @param text Input text to categorize
     * @return Categorization with confidence score
     */
    public AiResponse categorise(String text) {
        Map<String, Object> payload = new HashMap<>();
        payload.put("text", text);
        
        return callEndpoint("/categorise", payload, "categorise");
    }
    
    /**
     * Call /generate-report endpoint with streaming support
     * 
     * @param itemId ID of item to generate report for
     * @param content Document content
     * @return Generated report
     */
    public AiResponse generateReport(String itemId, String content) {
        Map<String, Object> payload = new HashMap<>();
        payload.put("item_id", itemId);
        payload.put("content", content);
        
        return callEndpoint("/generate-report", payload, "generate-report");
    }
    
    /**
     * Call /query endpoint for RAG-based queries
     * 
     * @param question User question
     * @return Answer with sources
     */
    public AiResponse query(String question) {
        Map<String, Object> payload = new HashMap<>();
        payload.put("question", question);
        
        return callEndpoint("/query", payload, "query");
    }
    
    /**
     * Call /analyse-document endpoint
     * 
     * @param text Document text to analyze
     * @return Array of insights and risks
     */
    public AiResponse analyseDocument(String text) {
        Map<String, Object> payload = new HashMap<>();
        payload.put("text", text);
        
        return callEndpoint("/analyse-document", payload, "analyse-document");
    }
    
    /**
     * Call /batch-process endpoint
     * 
     * @param items List of items to process
     * @param endpoint Specific endpoint to use
     * @return Batch results
     */
    public AiResponse batchProcess(List<String> items, String endpoint) {
        Map<String, Object> payload = new HashMap<>();
        payload.put("items", items);
        payload.put("endpoint", endpoint);
        
        return callEndpoint("/batch-process", payload, "batch-process");
    }
    
    /**
     * Check AI service health
     * 
     * @return Health status
     */
    public boolean healthCheck() {
        try {
            String url = aiServiceUrl + "/health";
            ResponseEntity<Map> response = restTemplate.getForEntity(url, Map.class);
            
            return response.getStatusCode() == HttpStatus.OK;
        } catch (Exception e) {
            logger.error("AI service health check failed: {}", e.getMessage());
            return false;
        }
    }
    
    /**
     * Core method to call AI service endpoints with retry logic
     * 
     * @param endpoint Target endpoint path
     * @param payload Request payload
     * @param fallbackKey Key for fallback response
     * @return Response from AI service or fallback
     */
    private AiResponse callEndpoint(String endpoint, Map<String, Object> payload, String fallbackKey) {
        String fullUrl = aiServiceUrl + endpoint;
        int attempt = 0;
        
        while (attempt < maxRetries) {
            try {
                logger.debug("Calling AI endpoint: {} (attempt {}/{})", fullUrl, attempt + 1, maxRetries);
                
                // Create request headers
                HttpHeaders headers = new HttpHeaders();
                headers.setContentType(MediaType.APPLICATION_JSON);
                headers.set("User-Agent", "Audit-Report-Generator/1.0");
                headers.set("X-Request-ID", UUID.randomUUID().toString());
                
                // Create request entity
                HttpEntity<Map<String, Object>> request = new HttpEntity<>(payload, headers);
                
                // Execute request with timeout
                long startTime = System.currentTimeMillis();
                ResponseEntity<Map> response = restTemplate.exchange(
                    fullUrl,
                    HttpMethod.POST,
                    request,
                    Map.class
                );
                long duration = System.currentTimeMillis() - startTime;
                
                logger.debug("AI service response received in {}ms with status {}", duration, response.getStatusCode());
                
                if (response.getStatusCode() == HttpStatus.OK) {
                    Map<String, Object> responseBody = response.getBody();
                    
                    // Extract metadata
                    Map<String, Object> meta = (Map<String, Object>) responseBody.getOrDefault("meta", new HashMap<>());
                    meta.put("response_time_ms", duration);
                    meta.put("cached", false);
                    
                    AiResponse aiResponse = new AiResponse();
                    aiResponse.result = objectMapper.writeValueAsString(responseBody.get("result"));
                    aiResponse.meta = meta;
                    aiResponse.isFallback = false;
                    
                    return aiResponse;
                }
                
                // Non-OK response
                logger.warn("AI service returned status {}: {}", response.getStatusCode(), response.getBody());
                throw new RestClientException("AI service returned " + response.getStatusCode());
                
            } catch (RestClientException e) {
                attempt++;
                logger.warn("AI service call failed (attempt {}/{}): {}", attempt, maxRetries, e.getMessage());
                
                if (attempt < maxRetries) {
                    // Exponential backoff
                    long delayMs = (long) (retryDelayMs * Math.pow(2, attempt - 1));
                    logger.debug("Retrying after {}ms", delayMs);
                    
                    try {
                        Thread.sleep(delayMs);
                    } catch (InterruptedException ie) {
                        Thread.currentThread().interrupt();
                        break;
                    }
                } else {
                    logger.error("Max retries ({}) exceeded for endpoint: {}", maxRetries, endpoint);
                    return getFallbackResponse(fallbackKey, e.getMessage());
                }
                
            } catch (Exception e) {
                logger.error("Unexpected error calling AI service: {}", e.getMessage(), e);
                return getFallbackResponse(fallbackKey, e.getMessage());
            }
        }
        
        return getFallbackResponse(fallbackKey, "Service unavailable after retries");
    }
    
    /**
     * Get fallback response when AI service is unavailable
     * 
     * @param endpoint Endpoint name
     * @param errorMessage Error message
     * @return Fallback response
     */
    private AiResponse getFallbackResponse(String endpoint, String errorMessage) {
        logger.info("Returning fallback response for endpoint: {}", endpoint);
        
        AiResponse response = new AiResponse();
        response.result = FALLBACK_RESPONSES.getOrDefault(endpoint, "Service temporarily unavailable");
        response.isFallback = true;
        response.error = errorMessage;
        
        Map<String, Object> meta = new HashMap<>();
        meta.put("is_fallback", true);
        meta.put("fallback_reason", errorMessage);
        meta.put("confidence", 0.0);
        response.meta = meta;
        
        return response;
    }
    
    /**
     * Validate AI service connectivity
     * 
     * @return true if service is reachable
     */
    public boolean isServiceAvailable() {
        try {
            String healthUrl = aiServiceUrl + "/health";
            ResponseEntity<Map> response = restTemplate.getForEntity(healthUrl, Map.class);
            
            boolean available = response.getStatusCode() == HttpStatus.OK;
            logger.info("AI service availability check: {}", available ? "ONLINE" : "OFFLINE");
            
            return available;
        } catch (Exception e) {
            logger.warn("AI service availability check failed: {}", e.getMessage());
            return false;
        }
    }
    
    /**
     * Get service metrics/stats
     * 
     * @return Service statistics
     */
    public Map<String, Object> getServiceStats() {
        try {
            String statsUrl = aiServiceUrl + "/stats";
            ResponseEntity<Map> response = restTemplate.getForEntity(statsUrl, Map.class);
            
            if (response.getStatusCode() == HttpStatus.OK) {
                return response.getBody();
            }
        } catch (Exception e) {
            logger.warn("Could not retrieve service stats: {}", e.getMessage());
        }
        
        return new HashMap<>();
    }
    
    // Setters for testing
    public void setAiServiceUrl(String url) {
        this.aiServiceUrl = url;
    }
    
    public void setTimeoutMs(int timeout) {
        this.timeoutMs = timeout;
    }
    
    public void setMaxRetries(int retries) {
        this.maxRetries = retries;
    }
}
