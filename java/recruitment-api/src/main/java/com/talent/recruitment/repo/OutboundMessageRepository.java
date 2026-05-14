package com.talent.recruitment.repo;

import com.talent.recruitment.domain.OutboundMessage;
import org.springframework.data.jpa.repository.JpaRepository;

public interface OutboundMessageRepository extends JpaRepository<OutboundMessage, Long> {}
