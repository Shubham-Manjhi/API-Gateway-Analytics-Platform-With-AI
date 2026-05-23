package com.platform.analytics.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.springframework.data.annotation.Id;
import org.springframework.data.elasticsearch.annotations.*;

import java.time.Instant;

/** Elasticsearch document stored in the 'api-events' index for every API call. */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Document(indexName = "api-events")
@Setting(settingPath = "elasticsearch/settings.json")
public class ApiEventDocument {

    @Id
    private String id;

    @Field(type = FieldType.Date, format = DateFormat.date_time)
    private Instant timestamp;

    @Field(type = FieldType.Keyword)
    private String tenantId;

    @Field(type = FieldType.Keyword)
    private String correlationId;

    @Field(type = FieldType.Keyword)
    private String method;

    @Field(type = FieldType.Keyword)
    private String path;

    @Field(type = FieldType.Keyword)
    private String host;

    @Field(type = FieldType.Integer)
    private int statusCode;

    @Field(type = FieldType.Long)
    private long latencyMs;

    @Field(type = FieldType.Keyword)
    private String clientIp;

    @Field(type = FieldType.Text)
    private String userAgent;

    @Field(type = FieldType.Boolean)
    private boolean error;

    @Field(type = FieldType.Text)
    private String errorMessage;

    @Field(type = FieldType.Keyword)
    private String serviceName;

    /** Composite field: "METHOD /path" for easy aggregation. */
    @Field(type = FieldType.Keyword)
    private String endpoint;
}
