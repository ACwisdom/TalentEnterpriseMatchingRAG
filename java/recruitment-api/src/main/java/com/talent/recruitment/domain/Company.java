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
@Table(name = "company")
@Getter
@Setter
public class Company {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String name;

    private String industry;
    private String scale;
    @Column(name = "contact_person")
    private String contactPerson;
    private String phone;
    private String address;
    private String status;
    @Column(name = "source_excel_row")
    private Integer sourceExcelRow;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();
}
