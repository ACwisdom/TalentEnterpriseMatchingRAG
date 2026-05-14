package com.talent.recruitment.web;

import com.talent.recruitment.domain.Communication;
import com.talent.recruitment.domain.Recommendation;
import com.talent.recruitment.domain.RecommendationStatus;
import com.talent.recruitment.service.CommunicationWriteService;
import com.talent.recruitment.service.IdempotencyService;
import com.talent.recruitment.service.RecommendationService;
import com.talent.recruitment.web.dto.CommunicationDto;
import com.talent.recruitment.web.dto.CreateCommunicationRequest;
import com.talent.recruitment.web.dto.CreateRecommendationRequest;
import com.talent.recruitment.web.dto.PatchRecommendationStatusRequest;
import com.talent.recruitment.web.dto.RecommendationDto;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
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
public class RecommendationsV1Controller {

    private final RecommendationService recommendationService;
    private final CommunicationWriteService communicationWriteService;
    private final IdempotencyService idempotencyService;

    @PostMapping
    public ResponseEntity<RecommendationDto> create(
            @RequestHeader(value = "Idempotency-Key", required = false) String idempotencyKey,
            @Valid @RequestBody CreateRecommendationRequest req) {
        return idempotencyService.execute(
                idempotencyKey,
                "POST:/api/v1/recommendations",
                RecommendationDto.class,
                () -> {
                    Recommendation r =
                            recommendationService.create(
                                    req.jobId(), req.candidateId(), req.reason(), req.matchScore(), req.scoreModel());
                    return ResponseEntity.status(HttpStatus.CREATED).body(WebMapper.toRecommendationDto(r));
                });
    }

    @PatchMapping("/{id}/status")
    public RecommendationDto patchStatus(@PathVariable Long id, @Valid @RequestBody PatchRecommendationStatusRequest req) {
        RecommendationStatus next = RecommendationStatus.fromValue(req.status());
        Recommendation r = recommendationService.patchStatus(id, next, req.note());
        return WebMapper.toRecommendationDto(r);
    }

    @PostMapping("/{id}/communications")
    public ResponseEntity<CommunicationDto> addCommunication(
            @RequestHeader(value = "Idempotency-Key", required = false) String idempotencyKey,
            @PathVariable Long id,
            @Valid @RequestBody CreateCommunicationRequest req) {
        String scope = "POST:/api/v1/recommendations/" + id + "/communications";
        return idempotencyService.execute(
                idempotencyKey,
                scope,
                CommunicationDto.class,
                () -> {
                    Communication c =
                            communicationWriteService.create(
                                    id, req.channel(), req.body(), null, null, req.direction());
                    return ResponseEntity.status(HttpStatus.CREATED).body(WebMapper.toCommunicationDto(c));
                });
    }
}
