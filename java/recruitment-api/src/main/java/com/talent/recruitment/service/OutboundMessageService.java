package com.talent.recruitment.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.talent.recruitment.domain.OutboundMessage;
import com.talent.recruitment.repo.OutboundMessageRepository;
import java.util.Map;
import java.util.UUID;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
public class OutboundMessageService {

    private final OutboundMessageRepository outboundMessageRepository;
    private final ObjectMapper objectMapper;

    @Transactional
    public OutboundMessage enqueue(
            String channel, Long candidateId, Long jobId, Long recommendationId, String templateCode, Map<String, Object> variables)
            throws JsonProcessingException {
        OutboundMessage m = new OutboundMessage();
        m.setDeliveryId(UUID.randomUUID().toString().replace("-", ""));
        m.setChannel(channel);
        m.setCandidateId(candidateId);
        m.setJobId(jobId);
        m.setRecommendationId(recommendationId);
        m.setTemplateCode(templateCode);
        m.setPayloadJson(variables == null ? null : objectMapper.writeValueAsString(variables));
        m.setStatus("QUEUED");
        return outboundMessageRepository.save(m);
    }

    @Transactional
    public OutboundMessage enqueueSimple(String to, String body) {
        try {
            Map<String, Object> vars =
                    Map.of("to", to == null ? "" : to, "body", body == null ? "" : body);
            return enqueue("APP", null, null, null, "OUTBOUND_RAW", vars);
        } catch (JsonProcessingException e) {
            throw new IllegalStateException(e);
        }
    }
}
