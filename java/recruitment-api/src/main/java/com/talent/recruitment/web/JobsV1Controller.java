package com.talent.recruitment.web;

import com.talent.recruitment.service.SearchService;
import com.talent.recruitment.web.dto.JobDto;
import com.talent.recruitment.web.dto.PagedResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Pageable;
import org.springframework.data.web.PageableDefault;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/jobs")
@RequiredArgsConstructor
public class JobsV1Controller {

    private final SearchService searchService;

    @GetMapping("/search")
    public PagedResponse<JobDto> search(
            @RequestParam(required = false) Long companyId,
            @RequestParam(required = false) String title,
            @RequestParam(required = false) String status,
            @PageableDefault(size = 20) Pageable pageable) {
        return PagedResponse.of(searchService.searchJobs(companyId, title, status, pageable));
    }
}
