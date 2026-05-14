package com.talent.recruitment.web;

import com.talent.recruitment.service.SearchService;
import com.talent.recruitment.web.dto.CandidateDto;
import com.talent.recruitment.web.dto.PagedResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Pageable;
import org.springframework.data.web.PageableDefault;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/candidates")
@RequiredArgsConstructor
public class CandidatesV1Controller {

    private final SearchService searchService;

    @GetMapping("/search")
    public PagedResponse<CandidateDto> search(
            @RequestParam(required = false) String name,
            @RequestParam(required = false) String email,
            @RequestParam(required = false) String skill,
            @PageableDefault(size = 20) Pageable pageable) {
        return PagedResponse.of(searchService.searchCandidates(name, email, skill, pageable));
    }
}
