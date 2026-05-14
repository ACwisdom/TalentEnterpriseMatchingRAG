package com.talent.recruitment.web;

import com.talent.recruitment.domain.OutboundMessage;
import com.talent.recruitment.service.IdempotencyService;
import com.talent.recruitment.service.OutboundMessageService;
import com.talent.recruitment.web.dto.OutboundMessageAcceptedDto;
import com.talent.recruitment.web.dto.OutboundMessageRequest;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/messages")
@RequiredArgsConstructor
public class MessagesV1Controller {

    private final OutboundMessageService outboundMessageService;
    private final IdempotencyService idempotencyService;

    @PostMapping("/outbound")
    public ResponseEntity<OutboundMessageAcceptedDto> outbound(
            @RequestHeader(value = "Idempotency-Key", required = false) String idempotencyKey,
            @Valid @RequestBody OutboundMessageRequest req) {
        return idempotencyService.execute(
                idempotencyKey,
                "POST:/api/v1/messages/outbound",
                OutboundMessageAcceptedDto.class,
                () -> {
                    OutboundMessage m = outboundMessageService.enqueueSimple(req.to(), req.body());
                    return ResponseEntity.accepted()
                            .body(
                                    OutboundMessageAcceptedDto.builder()
                                            .deliveryId(m.getDeliveryId())
                                            .status("QUEUED")
                                            .build());
                });
    }
}
