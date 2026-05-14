package com.talent.recruitment.web;

import com.talent.recruitment.service.JobSearchService;
import com.talent.recruitment.web.dto.JobDto;
import com.talent.recruitment.web.dto.PageInfo;
import com.talent.recruitment.web.dto.PagedResponse;
import java.math.BigDecimal;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.PageRequest;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/jobs")
@RequiredArgsConstructor
public class JobSearchController {

    private final JobSearchService jobSearchService;

    @GetMapping("/search")
    public PagedResponse<JobDto> search(
            @RequestParam(required = false) Long candidateId,
            @RequestParam(required = false) String titleKeyword,
            @RequestParam(required = false) String city,
            @RequestParam(required = false) BigDecimal salaryMin,
            @RequestParam(required = false) BigDecimal salaryMax,
            @RequestParam(required = false) String q,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        var pg = PageRequest.of(Math.max(0, page), Math.min(200, Math.max(1, size)));
        var result = jobSearchService.search(candidateId, titleKeyword, city, salaryMin, salaryMax, q, pg);
        return PagedResponse.<JobDto>builder()
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
