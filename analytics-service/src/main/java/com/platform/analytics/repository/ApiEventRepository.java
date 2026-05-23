package com.platform.analytics.repository;

import com.platform.analytics.model.ApiEventDocument;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.elasticsearch.repository.ElasticsearchRepository;
import org.springframework.stereotype.Repository;

import java.time.Instant;
import java.util.List;

@Repository
public interface ApiEventRepository extends ElasticsearchRepository<ApiEventDocument, String> {

    Page<ApiEventDocument> findByTenantId(String tenantId, Pageable pageable);

    List<ApiEventDocument> findByTenantIdAndTimestampBetween(String tenantId, Instant from, Instant to);

    Page<ApiEventDocument> findByTenantIdAndTimestampBetween(
            String tenantId, Instant from, Instant to, Pageable pageable);

    Page<ApiEventDocument> findByTenantIdAndErrorIsTrue(String tenantId, Pageable pageable);

    long countByTenantIdAndTimestampBetween(String tenantId, Instant from, Instant to);

    long countByTenantIdAndErrorIsTrueAndTimestampBetween(String tenantId, Instant from, Instant to);

    List<ApiEventDocument> findByTimestampBetween(Instant from, Instant to);
}
