package com.talent.recruitment;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.talent.recruitment.domain.Candidate;
import com.talent.recruitment.domain.Company;
import com.talent.recruitment.domain.Job;
import com.talent.recruitment.repo.CandidateRepository;
import com.talent.recruitment.repo.CompanyRepository;
import com.talent.recruitment.repo.JobRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.transaction.annotation.Transactional;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
@Transactional
class RecruitmentApiIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @Autowired
    private CompanyRepository companyRepository;

    @Autowired
    private JobRepository jobRepository;

    @Autowired
    private CandidateRepository candidateRepository;

    private Long jobId;
    private Long candidateId;

    @BeforeEach
    void seed() {
        Company company = new Company();
        company.setName("测试企业");
        company = companyRepository.save(company);

        Job job = new Job();
        job.setCompany(company);
        job.setTitle("算法工程师");
        job.setStatus("open");
        job = jobRepository.save(job);
        jobId = job.getId();

        Candidate candidate = new Candidate();
        candidate.setName("张三");
        candidate.setEmail("zhang@test.dev");
        candidate = candidateRepository.save(candidate);
        candidateId = candidate.getId();
    }

    @Test
    void createRecommendation_duplicateReturns409() throws Exception {
        String body = "{\"jobId\":%d,\"candidateId\":%d}".formatted(jobId, candidateId);
        mockMvc.perform(
                        post("/api/v1/recommendations")
                                .header("X-API-Key", "test-api-key")
                                .contentType(MediaType.APPLICATION_JSON)
                                .content(body))
                .andExpect(status().isCreated());

        mockMvc.perform(
                        post("/api/v1/recommendations")
                                .header("X-API-Key", "test-api-key")
                                .contentType(MediaType.APPLICATION_JSON)
                                .content(body))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.code").value("DUPLICATE_RECOMMENDATION"));
    }

    @Test
    void patchStatus_invalidTransitionReturns422() throws Exception {
        String create = "{\"jobId\":%d,\"candidateId\":%d}".formatted(jobId, candidateId);
        String json =
                mockMvc.perform(
                                post("/api/v1/recommendations")
                                        .header("X-API-Key", "test-api-key")
                                        .contentType(MediaType.APPLICATION_JSON)
                                        .content(create))
                        .andExpect(status().isCreated())
                        .andReturn()
                        .getResponse()
                        .getContentAsString();
        JsonNode node = objectMapper.readTree(json);
        long id = node.get("id").asLong();

        mockMvc.perform(
                        patch("/api/v1/recommendations/" + id + "/status")
                                .header("X-API-Key", "test-api-key")
                                .contentType(MediaType.APPLICATION_JSON)
                                .content("{\"status\":\"已读\"}"))
                .andExpect(status().isOk());

        mockMvc.perform(
                        patch("/api/v1/recommendations/" + id + "/status")
                                .header("X-API-Key", "test-api-key")
                                .contentType(MediaType.APPLICATION_JSON)
                                .content("{\"status\":\"面试\"}"))
                .andExpect(status().isUnprocessableEntity())
                .andExpect(jsonPath("$.code").value("INVALID_STATUS_TRANSITION"));
    }
}
