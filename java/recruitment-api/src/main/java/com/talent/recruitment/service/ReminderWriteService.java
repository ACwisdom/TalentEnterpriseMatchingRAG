package com.talent.recruitment.service;

import com.talent.recruitment.api.BusinessException;
import com.talent.recruitment.domain.Recommendation;
import com.talent.recruitment.domain.Reminder;
import com.talent.recruitment.repo.RecommendationRepository;
import com.talent.recruitment.repo.ReminderRepository;
import java.time.Instant;
import java.util.Map;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
public class ReminderWriteService {

    private final ReminderRepository reminderRepository;
    private final RecommendationRepository recommendationRepository;

    @Transactional
    public Reminder create(Long recommendationId, String message, Instant dueAt, String channel) {
        Reminder r = new Reminder();
        if (recommendationId != null) {
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
            r.setRecommendation(rec);
        }
        r.setTitle(message);
        r.setRemindAt(dueAt);
        r.setChannel(channel != null && !channel.isBlank() ? channel : "APP");
        r.setStatus("PENDING");
        return reminderRepository.save(r);
    }
}
