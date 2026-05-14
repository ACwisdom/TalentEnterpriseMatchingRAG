package com.talent.recruitment.web;

import com.talent.recruitment.domain.Reminder;
import com.talent.recruitment.service.IdempotencyService;
import com.talent.recruitment.service.ReminderWriteService;
import com.talent.recruitment.web.dto.CreateReminderRequest;
import com.talent.recruitment.web.dto.ReminderDto;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/reminders")
@RequiredArgsConstructor
public class RemindersV1Controller {

    private final ReminderWriteService reminderWriteService;
    private final IdempotencyService idempotencyService;

    @PostMapping
    public ResponseEntity<ReminderDto> create(
            @RequestHeader(value = "Idempotency-Key", required = false) String idempotencyKey,
            @Valid @RequestBody CreateReminderRequest req) {
        return idempotencyService.execute(
                idempotencyKey,
                "POST:/api/v1/reminders",
                ReminderDto.class,
                () -> {
                    Reminder r =
                            reminderWriteService.create(req.recommendationId(), req.message(), req.dueAt(), null);
                    return ResponseEntity.status(HttpStatus.CREATED).body(WebMapper.toReminderDto(r));
                });
    }
}
