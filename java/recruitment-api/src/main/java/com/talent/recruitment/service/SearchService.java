package com.talent.recruitment.service;

import com.talent.recruitment.domain.Candidate;
import com.talent.recruitment.domain.Job;
import com.talent.recruitment.repo.CandidateRepository;
import com.talent.recruitment.repo.JobRepository;
import com.talent.recruitment.web.WebMapper;
import com.talent.recruitment.web.dto.CandidateDto;
import com.talent.recruitment.web.dto.JobDto;
import jakarta.persistence.criteria.Join;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.domain.Specification;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

@Service
@Transactional(readOnly = true)
public class SearchService {

    private final CandidateRepository candidateRepository;
    private final JobRepository jobRepository;

    public SearchService(CandidateRepository candidateRepository, JobRepository jobRepository) {
        this.candidateRepository = candidateRepository;
        this.jobRepository = jobRepository;
    }

    public Page<CandidateDto> searchCandidates(String name, String email, String skill, Pageable pageable) {
        Specification<Candidate> spec = (root, query, cb) -> cb.conjunction();
        if (StringUtils.hasText(name)) {
            String pattern = "%" + name.trim().toLowerCase() + "%";
            spec = spec.and((root, q, cb) -> cb.like(cb.lower(root.get("name")), pattern));
        }
        if (StringUtils.hasText(email)) {
            String pattern = "%" + email.trim().toLowerCase() + "%";
            spec = spec.and((root, q, cb) -> cb.like(cb.lower(root.get("email")), pattern));
        }
        if (StringUtils.hasText(skill)) {
            String pattern = "%" + skill.trim().toLowerCase() + "%";
            spec = spec.and((root, q, cb) -> cb.like(cb.lower(root.get("skills")), pattern));
        }
        return candidateRepository.findAll(spec, pageable).map(WebMapper::toCandidateDto);
    }

    public Page<JobDto> searchJobs(Long companyId, String title, String status, Pageable pageable) {
        Specification<Job> spec = (root, query, cb) -> cb.conjunction();
        if (companyId != null) {
            spec = spec.and((root, q, cb) -> {
                Join<Object, Object> company = root.join("company");
                return cb.equal(company.get("id"), companyId);
            });
        }
        if (StringUtils.hasText(title)) {
            String pattern = "%" + title.trim().toLowerCase() + "%";
            spec = spec.and((root, q, cb) -> cb.like(cb.lower(root.get("title")), pattern));
        }
        if (StringUtils.hasText(status)) {
            spec = spec.and((root, q, cb) -> cb.equal(cb.lower(root.get("status")), status.trim().toLowerCase()));
        }
        return jobRepository.findAll(spec, pageable).map(WebMapper::toJobDto);
    }
}
