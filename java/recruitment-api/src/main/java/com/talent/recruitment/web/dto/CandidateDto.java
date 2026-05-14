package com.talent.recruitment.web.dto;

import java.math.BigDecimal;
import java.time.Instant;

public record CandidateDto(
        Long id,
        String name,
        String phone,
        String email,
        String skills,
        Integer expYears,
        BigDecimal expectedSalaryMin,
        BigDecimal expectedSalaryMax,
        String city,
        String status,
        Instant createdAt) {}
