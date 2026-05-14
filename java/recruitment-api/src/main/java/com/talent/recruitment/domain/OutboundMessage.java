package com.talent.recruitment.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import lombok.Getter;
import lombok.Setter;

@Entity
@Table(name = "outbound_message")
@Getter
@Setter
public class OutboundMessage {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "delivery_id", nullable = false, unique = true, length = 64)
    private String deliveryId;

    @Column(nullable = false, length = 50)
    private String channel;

    @Column(name = "candidate_id")
    private Long candidateId;

    @Column(name = "job_id")
    private Long jobId;

    @Column(name = "recommendation_id")
    private Long recommendationId;

    @Column(name = "template_code")
    private String templateCode;

    @Column(name = "payload_json", columnDefinition = "TEXT")
    private String payloadJson;

    @Column(nullable = false)
    private String status = "QUEUED";

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();
}
