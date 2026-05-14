package com.talent.recruitment.web.dto;

import java.math.BigDecimal;
import java.time.Instant;

public record JobDto(
        Long id,
        Long companyId,
        String companyName,
        String title,
        String description,
        BigDecimal salaryMin,
        BigDecimal salaryMax,
        String city,
        Integer headcount,
        String urgency,
        String status,
        Instant createdAt,
        Instant updatedAt) {}
