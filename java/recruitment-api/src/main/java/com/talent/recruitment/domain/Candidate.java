package com.talent.recruitment.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.math.BigDecimal;
import java.time.Instant;
import lombok.Getter;
import lombok.Setter;

@Entity
@Table(name = "candidate")
@Getter
@Setter
public class Candidate {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String name;

    private String phone;
    private String email;

    @Column(name = "resume_text", columnDefinition = "TEXT")
    private String resumeText;

    private String skills;

    @Column(name = "exp_years")
    private Integer expYears;

    @Column(name = "expected_salary_min")
    private BigDecimal expectedSalaryMin;

    @Column(name = "expected_salary_max")
    private BigDecimal expectedSalaryMax;
    private String city;
    private String status;
    private String source;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();
}
