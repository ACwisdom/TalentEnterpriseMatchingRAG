package com.talent.recruitment.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.talent.recruitment.domain.IdempotencyRecord;
import com.talent.recruitment.repo.IdempotencyRecordRepository;
import java.time.Duration;
import java.time.Instant;
import java.util.Optional;
import java.util.concurrent.Callable;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

@Service
public class IdempotencyService {

    private static final Duration TTL = Duration.ofHours(24);

    private final IdempotencyRecordRepository repository;
    private final ObjectMapper objectMapper;

    public IdempotencyService(IdempotencyRecordRepository repository, ObjectMapper objectMapper) {
        this.repository = repository;
        this.objectMapper = objectMapper;
    }

    @Transactional
    public <T> ResponseEntity<T> execute(
            String idempotencyKey, String scope, Class<T> bodyClass, Callable<ResponseEntity<T>> action) {
        try {
            if (!StringUtils.hasText(idempotencyKey)) {
                return action.call();
            }
            Optional<IdempotencyRecord> existing = repository.findByIdempotencyKeyAndScope(idempotencyKey, scope);
            if (existing.isPresent()) {
                IdempotencyRecord r = existing.get();
                if (Instant.now().isBefore(r.getCreatedAt().plus(TTL))) {
                    T body = objectMapper.readValue(r.getResponseBody(), bodyClass);
                    return ResponseEntity.status(r.getHttpStatus()).body(body);
                }
                repository.delete(r);
                repository.flush();
            }

            ResponseEntity<T> fresh = action.call();
            String serialized = objectMapper.writeValueAsString(fresh.getBody());
            IdempotencyRecord saved = new IdempotencyRecord();
            saved.setIdempotencyKey(idempotencyKey);
            saved.setScope(scope);
            saved.setFingerprint("");
            saved.setHttpStatus(fresh.getStatusCode().value());
            saved.setResponseBody(serialized);
            saved.setCreatedAt(Instant.now());
            repository.save(saved);
            return fresh;
        } catch (JsonProcessingException ex) {
            throw new IllegalStateException("Idempotency serialization failed", ex);
        } catch (RuntimeException ex) {
            throw ex;
        } catch (Exception ex) {
            throw new IllegalStateException(ex);
        }
    }
}
