package com.talent.recruitment.web.dto;

import jakarta.validation.constraints.NotNull;

public record CreateRecommendationRequest(
        @NotNull Long jobId,
        @NotNull Long candidateId,
        String reason,
        Double matchScore,
        String scoreModel) {}
