package com.talent.recruitment.web;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.talent.recruitment.service.IdempotencyService;
import com.talent.recruitment.service.RecommendationService;
import com.talent.recruitment.web.dto.CreateRecommendationRequest;
import com.talent.recruitment.web.dto.PatchRecommendationStatusRequest;
import com.talent.recruitment.web.dto.RecommendationDto;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.util.StringUtils;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/recommendations")
@RequiredArgsConstructor
public class RecommendationController {

    private static final String IDEM_SCOPE_CREATE = "RECOMMENDATION_CREATE";

    private final RecommendationService recommendationService;
    private final IdempotencyService idempotencyService;
    private final ObjectMapper objectMapper;

    @PostMapping
    public ResponseEntity<RecommendationDto> create(
            @Valid @RequestBody CreateRecommendationRequest req,
            @RequestHeader(value = "Idempotency-Key", required = false) String idempotencyKey)
            throws JsonProcessingException {
        String bodyJson = objectMapper.writeValueAsString(req);
        String fingerprint = idempotencyService.fingerprint(bodyJson);
        if (StringUtils.hasText(idempotencyKey)) {
            var replay = idempotencyService.findReplay(IDEM_SCOPE_CREATE, idempotencyKey, fingerprint);
            if (replay.isPresent()) {
                var dto = objectMapper.readValue(replay.get().getResponseBody(), RecommendationDto.class);
                return ResponseEntity.status(replay.get().getHttpStatus()).body(dto);
            }
        }

        var saved =
                recommendationService.create(
                        req.getJobId(), req.getCandidateId(), req.getReason(), req.getMatchScore(), req.getScoreModel());
        RecommendationDto dto = WebMapper.toDto(saved);
        String out = objectMapper.writeValueAsString(dto);
        if (StringUtils.hasText(idempotencyKey)) {
            idempotencyService.recordSuccess(IDEM_SCOPE_CREATE, idempotencyKey, fingerprint, HttpStatus.CREATED.value(), out);
        }
        return ResponseEntity.status(HttpStatus.CREATED).body(dto);
    }

    @PatchMapping("/{id}/status")
    public RecommendationDto patchStatus(
            @PathVariable long id, @Valid @RequestBody PatchRecommendationStatusRequest req) {
        var saved = recommendationService.patchStatus(id, req.getStatus(), req.getNote());
        return WebMapper.toDto(saved);
    }
}
