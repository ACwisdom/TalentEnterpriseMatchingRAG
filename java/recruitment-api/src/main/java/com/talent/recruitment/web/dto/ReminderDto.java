package com.talent.recruitment.web.dto;

import java.time.Instant;

public record ReminderDto(
        Long id, Long recommendationId, String message, Instant dueAt, String channel, String status, Instant createdAt) {}
