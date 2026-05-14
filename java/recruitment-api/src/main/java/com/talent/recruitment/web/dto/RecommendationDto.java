package com.talent.recruitment.web.dto;

import com.talent.recruitment.domain.RecommendationStatus;
import java.time.Instant;

public record RecommendationDto(
        Long id,
        Long jobId,
        Long candidateId,
        Double matchScore,
        String scoreModel,
        String reason,
        RecommendationStatus status,
        Instant createdAt,
        Instant updatedAt) {}
