package com.talent.recruitment.web;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.talent.recruitment.service.IdempotencyService;
import com.talent.recruitment.service.OutboundMessageService;
import com.talent.recruitment.web.dto.OutboundMessageAcceptedDto;
import com.talent.recruitment.web.dto.OutboundMessageRequest;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.util.StringUtils;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/messages")
@RequiredArgsConstructor
public class OutboundMessageController {

    private static final String IDEM_SCOPE = "OUTBOUND_MESSAGE";

    private final OutboundMessageService outboundMessageService;
    private final IdempotencyService idempotencyService;
    private final ObjectMapper objectMapper;

    @PostMapping("/outbound")
    public ResponseEntity<OutboundMessageAcceptedDto> outbound(
            @Valid @RequestBody OutboundMessageRequest req,
            @RequestHeader(value = "Idempotency-Key", required = false) String idempotencyKey)
            throws JsonProcessingException {
        String bodyJson = objectMapper.writeValueAsString(req);
        String fingerprint = idempotencyService.fingerprint(bodyJson);
        if (StringUtils.hasText(idempotencyKey)) {
            var replay = idempotencyService.findReplay(IDEM_SCOPE, idempotencyKey, fingerprint);
            if (replay.isPresent()) {
                var dto = objectMapper.readValue(replay.get().getResponseBody(), OutboundMessageAcceptedDto.class);
                return ResponseEntity.status(replay.get().getHttpStatus()).body(dto);
            }
        }

        var saved =
                outboundMessageService.enqueue(
                        req.getChannel(),
                        req.getCandidateId(),
                        req.getJobId(),
                        req.getRecommendationId(),
                        req.getTemplateCode(),
                        req.getVariables());
        var dto =
                OutboundMessageAcceptedDto.builder().deliveryId(saved.getDeliveryId()).status(saved.getStatus()).build();
        String out = objectMapper.writeValueAsString(dto);
        if (StringUtils.hasText(idempotencyKey)) {
            idempotencyService.recordSuccess(IDEM_SCOPE, idempotencyKey, fingerprint, HttpStatus.ACCEPTED.value(), out);
        }
        return ResponseEntity.status(HttpStatus.ACCEPTED).body(dto);
    }
}
