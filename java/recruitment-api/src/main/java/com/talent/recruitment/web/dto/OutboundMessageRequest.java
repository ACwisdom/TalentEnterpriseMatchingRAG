package com.talent.recruitment.web.dto;

import jakarta.validation.constraints.NotBlank;

public record OutboundMessageRequest(String to, @NotBlank String body) {}
