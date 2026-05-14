package com.talent.recruitment.service;

import com.talent.recruitment.api.BusinessException;
import com.talent.recruitment.domain.Candidate;
import com.talent.recruitment.domain.Job;
import com.talent.recruitment.domain.Recommendation;
import com.talent.recruitment.domain.RecommendationStatus;
import com.talent.recruitment.repo.CandidateRepository;
import com.talent.recruitment.repo.JobRepository;
import com.talent.recruitment.repo.RecommendationRepository;
import java.time.Instant;
import java.util.Map;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
public class RecommendationService {

    private final RecommendationRepository recommendationRepository;
    private final JobRepository jobRepository;
    private final CandidateRepository candidateRepository;

    @Transactional
    public Recommendation create(
            Long jobId, Long candidateId, String reason, Double matchScore, String scoreModel) {
        Job job =
                jobRepository
                        .findById(jobId)
                        .orElseThrow(
                                () ->
                                        new BusinessException(
                                                "JOB_NOT_FOUND",
                                                HttpStatus.NOT_FOUND,
                                                "Job not found",
                                                Map.of("jobId", jobId)));
        Candidate candidate =
                candidateRepository
                        .findById(candidateId)
                        .orElseThrow(
                                () ->
                                        new BusinessException(
                                                "CANDIDATE_NOT_FOUND",
                                                HttpStatus.NOT_FOUND,
                                                "Candidate not found",
                                                Map.of("candidateId", candidateId)));

        if (!"open".equalsIgnoreCase(job.getStatus())) {
            throw new BusinessException(
                    "JOB_NOT_OPEN",
                    HttpStatus.UNPROCESSABLE_ENTITY,
                    "Job is not open for recommendations",
                    Map.of("jobId", jobId, "status", job.getStatus()));
        }

        recommendationRepository
                .findByJob_IdAndCandidate_Id(jobId, candidateId)
                .ifPresent(
                        existing -> {
                            throw new BusinessException(
                                    "DUPLICATE_RECOMMENDATION",
                                    HttpStatus.CONFLICT,
                                    "Recommendation already exists",
                                    Map.of("existingId", existing.getId(), "jobId", jobId, "candidateId", candidateId));
                        });

        Recommendation r = new Recommendation();
        r.setJob(job);
        r.setCandidate(candidate);
        r.setReason(reason);
        r.setMatchScore(matchScore);
        r.setScoreModel(scoreModel);
        r.setStatus(RecommendationStatus.已推荐);
        Instant now = Instant.now();
        r.setCreatedAt(now);
        r.setUpdatedAt(now);
        return recommendationRepository.save(r);
    }

    @Transactional
    public Recommendation patchStatus(Long id, RecommendationStatus next, String note) {
        Recommendation r =
                recommendationRepository
                        .findById(id)
                        .orElseThrow(
                                () ->
                                        new BusinessException(
                                                "RECOMMENDATION_NOT_FOUND",
                                                HttpStatus.NOT_FOUND,
                                                "Recommendation not found",
                                                Map.of("recommendationId", id)));

        if (r.getStatus() == next) {
            return r;
        }
        if (RecommendationStatus.isTerminal(r.getStatus())) {
            throw new BusinessException(
                    "INVALID_STATUS_TRANSITION",
                    HttpStatus.UNPROCESSABLE_ENTITY,
                    "Terminal status cannot change",
                    Map.of("current", r.getStatus().getValue(), "requested", next.getValue()));
        }
        if (!RecommendationStatus.allowedNext(r.getStatus()).contains(next)) {
            throw new BusinessException(
                    "INVALID_STATUS_TRANSITION",
                    HttpStatus.UNPROCESSABLE_ENTITY,
                    "Illegal status transition",
                    Map.of("current", r.getStatus().getValue(), "requested", next.getValue()));
        }
        if (note != null && !note.isBlank()) {
            String base = r.getReason() == null ? "" : r.getReason();
            r.setReason(base + (base.isEmpty() ? "" : "\n") + "[status_note] " + note);
        }
        r.setStatus(next);
        r.setUpdatedAt(Instant.now());
        return recommendationRepository.save(r);
    }
}
