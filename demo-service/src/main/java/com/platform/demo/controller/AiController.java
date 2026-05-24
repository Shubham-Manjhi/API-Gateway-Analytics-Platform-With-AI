package com.platform.demo.controller;

import com.platform.demo.model.AiAnalysisRequest;
import com.platform.demo.model.AiAnalysisResponse;
import com.platform.demo.service.AiService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@Slf4j
@RestController
@RequestMapping("/demo/ai")
@RequiredArgsConstructor
@CrossOrigin(origins = "*")
public class AiController {

    private final AiService aiService;

    /**
     * POST /demo/ai/analyze
     * Body: { "action": "understand", "contextType": "error", "data": { ... } }
     */
    @PostMapping("/analyze")
    public ResponseEntity<AiAnalysisResponse> analyze(@RequestBody AiAnalysisRequest request) {
        log.info("AI analysis requested: action={} contextType={}", request.getAction(), request.getContextType());
        AiAnalysisResponse response = aiService.analyze(request);
        log.info("AI analysis completed: success={} latencyMs={}", response.isSuccess(), response.getLatencyMs());
        return ResponseEntity.ok(response);
    }
}

