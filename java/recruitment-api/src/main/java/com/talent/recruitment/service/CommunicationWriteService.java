package com.talent.recruitment.service;

import com.talent.recruitment.api.BusinessException;
import com.talent.recruitment.domain.Communication;
import com.talent.recruitment.domain.Recommendation;
import com.talent.recruitment.repo.CommunicationRepository;
import com.talent.recruitment.repo.RecommendationRepository;
import java.time.Instant;
import java.util.Map;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
public class CommunicationWriteService {

    private final CommunicationRepository communicationRepository;
    private final RecommendationRepository recommendationRepository;

    @Transactional
    public Communication create(
            Long recommendationId,
            String channel,
            String contentSummary,
            String nextStep,
            String nextTimeIso,
            String createdBy) {
        Recommendation rec =
                recommendationRepository
                        .findById(recommendationId)
                        .orElseThrow(
                                () ->
                                        new BusinessException(
                                                "RECOMMENDATION_NOT_FOUND",
                                                HttpStatus.NOT_FOUND,
                                                "Recommendation not found",
                                                Map.of("recommendationId", recommendationId)));
        Communication c = new Communication();
        c.setRecommendation(rec);
        c.setChannel(channel);
        c.setContentSummary(contentSummary);
        c.setNextStep(nextStep);
        if (nextTimeIso != null && !nextTimeIso.isBlank()) {
            c.setNextTime(Instant.parse(nextTimeIso));
        }
        c.setCreatedBy(createdBy);
        return communicationRepository.save(c);
    }
}
