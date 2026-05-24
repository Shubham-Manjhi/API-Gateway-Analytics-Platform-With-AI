package com.platform.demo.model;

import lombok.Data;
import java.util.Map;

@Data
public class AiAnalysisRequest {
    /** AI action id, e.g. "understand", "rootcause", "fix", "explain" */
    private String action;
    /** Context type: error | endpoint | alert | tenant | log | warn */
    private String contextType;
    /** All relevant data fields for the context */
    private Map<String, Object> data;
}

