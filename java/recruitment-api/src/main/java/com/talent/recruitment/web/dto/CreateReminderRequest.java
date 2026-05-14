package com.talent.recruitment.web.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import java.time.Instant;

public record CreateReminderRequest(Long recommendationId, @NotNull Instant dueAt, @NotBlank String message) {}
