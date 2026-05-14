package com.talent.recruitment.web;

import com.talent.recruitment.domain.Candidate;
import com.talent.recruitment.domain.Communication;
import com.talent.recruitment.domain.Job;
import com.talent.recruitment.domain.Recommendation;
import com.talent.recruitment.domain.Reminder;
import com.talent.recruitment.web.dto.CandidateDto;
import com.talent.recruitment.web.dto.CommunicationDto;
import com.talent.recruitment.web.dto.JobDto;
import com.talent.recruitment.web.dto.RecommendationDto;
import com.talent.recruitment.web.dto.ReminderDto;

public final class WebMapper {

    private WebMapper() {}

    public static CandidateDto toCandidateDto(Candidate c) {
        return new CandidateDto(
                c.getId(),
                c.getName(),
                c.getPhone(),
                c.getEmail(),
                c.getSkills(),
                c.getExpYears(),
                c.getExpectedSalaryMin(),
                c.getExpectedSalaryMax(),
                c.getCity(),
                c.getStatus(),
                c.getCreatedAt());
    }

    public static JobDto toJobDto(Job j) {
        return new JobDto(
                j.getId(),
                j.getCompany().getId(),
                j.getCompany().getName(),
                j.getTitle(),
                j.getDescription(),
                j.getSalaryMin(),
                j.getSalaryMax(),
                j.getCity(),
                j.getHeadcount(),
                j.getUrgency(),
                j.getStatus(),
                j.getCreatedAt(),
                j.getUpdatedAt());
    }

    public static RecommendationDto toRecommendationDto(Recommendation r) {
        return new RecommendationDto(
                r.getId(),
                r.getJob().getId(),
                r.getCandidate().getId(),
                r.getMatchScore(),
                r.getScoreModel(),
                r.getReason(),
                r.getStatus(),
                r.getCreatedAt(),
                r.getUpdatedAt());
    }

    /** Maps persistence: body from content_summary, direction from created_by. */
    public static CommunicationDto toCommunicationDto(Communication c) {
        return new CommunicationDto(
                c.getId(),
                c.getRecommendation().getId(),
                c.getChannel(),
                c.getCreatedBy(),
                c.getContentSummary(),
                c.getCreatedAt());
    }

    public static ReminderDto toReminderDto(Reminder r) {
        Long recId = r.getRecommendation() != null ? r.getRecommendation().getId() : null;
        return new ReminderDto(
                r.getId(), recId, r.getTitle(), r.getRemindAt(), r.getChannel(), r.getStatus(), r.getCreatedAt());
    }
}
