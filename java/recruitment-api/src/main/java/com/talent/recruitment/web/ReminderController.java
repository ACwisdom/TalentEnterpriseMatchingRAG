package com.talent.recruitment.web;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.talent.recruitment.service.IdempotencyService;
import com.talent.recruitment.service.ReminderWriteService;
import com.talent.recruitment.web.dto.CreateReminderRequest;
import com.talent.recruitment.web.dto.ReminderDto;
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
@RequestMapping("/api/v1/reminders")
@RequiredArgsConstructor
public class ReminderController {

    private static final String IDEM_SCOPE = "REMINDER_CREATE";

    private final ReminderWriteService reminderWriteService;
    private final IdempotencyService idempotencyService;
    private final ObjectMapper objectMapper;

    @PostMapping
    public ResponseEntity<ReminderDto> create(
            @Valid @RequestBody CreateReminderRequest req,
            @RequestHeader(value = "Idempotency-Key", required = false) String idempotencyKey)
            throws JsonProcessingException {
        String bodyJson = objectMapper.writeValueAsString(req);
        String fingerprint = idempotencyService.fingerprint(bodyJson);
        if (StringUtils.hasText(idempotencyKey)) {
            var replay = idempotencyService.findReplay(IDEM_SCOPE, idempotencyKey, fingerprint);
            if (replay.isPresent()) {
                var dto = objectMapper.readValue(replay.get().getResponseBody(), ReminderDto.class);
                return ResponseEntity.status(replay.get().getHttpStatus()).body(dto);
            }
        }

        var saved =
                reminderWriteService.create(
                        req.getRecommendationId(), req.getTitle(), req.getRemindAt(), req.getChannel());
        ReminderDto dto = WebMapper.toDto(saved);
        String out = objectMapper.writeValueAsString(dto);
        if (StringUtils.hasText(idempotencyKey)) {
            idempotencyService.recordSuccess(IDEM_SCOPE, idempotencyKey, fingerprint, HttpStatus.CREATED.value(), out);
        }
        return ResponseEntity.status(HttpStatus.CREATED).body(dto);
    }
}
