package com.talent.recruitment.web.dto;

import java.time.Instant;

public record CommunicationDto(
        Long id, Long recommendationId, String channel, String direction, String body, Instant createdAt) {}
