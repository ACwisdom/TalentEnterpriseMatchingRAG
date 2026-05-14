package com.talent.recruitment.web.dto;

import jakarta.validation.constraints.NotBlank;

public record CreateCommunicationRequest(
        @NotBlank String channel, @NotBlank String direction, @NotBlank String body) {}
