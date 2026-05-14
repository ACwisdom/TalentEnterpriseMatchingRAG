package com.talent.recruitment.web;

import com.talent.recruitment.service.CommunicationWriteService;
import com.talent.recruitment.web.dto.CommunicationDto;
import com.talent.recruitment.web.dto.CreateCommunicationRequest;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/recommendations")
@RequiredArgsConstructor
public class CommunicationController {

    private final CommunicationWriteService communicationWriteService;

    @PostMapping("/{id}/communications")
    @ResponseStatus(HttpStatus.CREATED)
    public CommunicationDto create(
            @PathVariable("id") long recommendationId, @Valid @RequestBody CreateCommunicationRequest req) {
        var saved =
                communicationWriteService.create(
                        recommendationId,
                        req.getChannel(),
                        req.getContentSummary(),
                        req.getNextStep(),
                        req.getNextTime(),
                        req.getCreatedBy());
        return WebMapper.toDto(saved);
    }
}
