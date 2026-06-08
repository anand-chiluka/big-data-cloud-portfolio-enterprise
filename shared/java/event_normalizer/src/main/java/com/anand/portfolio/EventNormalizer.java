package com.anand.portfolio;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;

/**
 * STAR
 * Situation: Downstream batch and streaming jobs depend on consistent event field names.
 * Task: Normalize raw JSON events using a stable Java component.
 * Action: Parse raw JSON, validate required fields, and emit normalized JSON.
 * Result: Shows enterprise Java capability in a big data portfolio without overcomplicating the repo.
 */
public class EventNormalizer {
    private static final ObjectMapper MAPPER = new ObjectMapper();

    public String normalize(String rawJson) throws Exception {
        JsonNode input = MAPPER.readTree(rawJson);
        ObjectNode output = MAPPER.createObjectNode();

        output.put("event_id", requireText(input, "event_id"));
        output.put("event_type", input.path("event_type").asText("unknown"));
        output.put("event_time", requireText(input, "event_time"));
        output.set("payload", input.path("payload"));

        return MAPPER.writeValueAsString(output);
    }

    private String requireText(JsonNode node, String field) {
        if (!node.hasNonNull(field) || node.get(field).asText().isBlank()) {
            throw new IllegalArgumentException("Missing required field: " + field);
        }
        return node.get(field).asText();
    }
}
