package com.talent.recruitment.web.dto;

import jakarta.validation.constraints.NotBlank;

public record PatchRecommendationStatusRequest(@NotBlank String status, String note) {}
