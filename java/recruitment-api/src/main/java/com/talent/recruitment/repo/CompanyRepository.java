package com.talent.recruitment.repo;

import com.talent.recruitment.domain.Company;
import org.springframework.data.jpa.repository.JpaRepository;

public interface CompanyRepository extends JpaRepository<Company, Long> {}
