package com.talent.recruitment.repo;

import com.talent.recruitment.domain.Reminder;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ReminderRepository extends JpaRepository<Reminder, Long> {}
