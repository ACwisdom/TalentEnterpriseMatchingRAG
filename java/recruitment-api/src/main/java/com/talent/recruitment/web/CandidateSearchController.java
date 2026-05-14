package com.talent.recruitment.web;

import com.talent.recruitment.service.CandidateSearchService;
import com.talent.recruitment.web.dto.CandidateDto;
import com.talent.recruitment.web.dto.PageInfo;
import com.talent.recruitment.web.dto.PagedResponse;
import java.math.BigDecimal;
import java.util.List;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.PageRequest;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/candidates")
@RequiredArgsConstructor
public class CandidateSearchController {

    private final CandidateSearchService candidateSearchService;

    @GetMapping("/search")
    public PagedResponse<CandidateDto> search(
            @RequestParam(name = "skill", required = false) List<String> skills,
            @RequestParam(required = false) String city,
            @RequestParam(required = false) BigDecimal salaryMin,
            @RequestParam(required = false) BigDecimal salaryMax,
            @RequestParam(required = false) Integer expYearsMin,
            @RequestParam(required = false) String q,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        var pg = PageRequest.of(Math.max(0, page), Math.min(200, Math.max(1, size)));
        var result = candidateSearchService.search(skills, city, salaryMin, salaryMax, expYearsMin, q, pg);
        return PagedResponse.<CandidateDto>builder()
                .items(result.getContent().stream().map(WebMapper::toDto).toList())
                .page(
                        PageInfo.builder()
                                .number(result.getNumber())
                                .size(result.getSize())
                                .totalElements(result.getTotalElements())
                                .totalPages(result.getTotalPages())
                                .build())
                .build();
    }
}
