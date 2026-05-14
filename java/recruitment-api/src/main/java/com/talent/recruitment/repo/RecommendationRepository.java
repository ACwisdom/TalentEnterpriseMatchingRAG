package com.talent.recruitment.repo;

import com.talent.recruitment.domain.Recommendation;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface RecommendationRepository extends JpaRepository<Recommendation, Long> {

    Optional<Recommendation> findByJob_IdAndCandidate_Id(Long jobId, Long candidateId);
}
