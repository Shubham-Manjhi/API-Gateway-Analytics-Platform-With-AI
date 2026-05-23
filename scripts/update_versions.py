#!/usr/bin/env python3
"""Updates build files for Java 25 + Gradle 9.3.0 + Spring Boot 3.4.4 compatibility."""
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def write(rel, content):
    p = os.path.join(BASE, rel)
    with open(p, 'w') as f:
        f.write(content)
    print(f"  updated: {rel}")

write("gradle/wrapper/gradle-wrapper.properties",
"distributionBase=GRADLE_USER_HOME\n"
"distributionPath=wrapper/dists\n"
"distributionUrl=https\\://services.gradle.org/distributions/gradle-9.3.0-bin.zip\n"
"networkTimeout=10000\n"
"validateDistributionUrl=true\n"
"zipStoreBase=GRADLE_USER_HOME\n"
"zipStorePath=wrapper/dists\n")

write("build.gradle",
"plugins {\n"
"    id 'org.springframework.boot' version '3.4.4' apply false\n"
"    id 'io.spring.dependency-management' version '1.1.7' apply false\n"
"}\n\n"
"allprojects {\n"
"    group = 'com.platform'\n"
"    version = '1.0.0'\n"
"    repositories { mavenCentral() }\n"
"}\n\n"
"subprojects {\n"
"    apply plugin: 'java'\n"
"    java {\n"
"        toolchain { languageVersion = JavaLanguageVersion.of(21) }\n"
"    }\n"
"    dependencies {\n"
"        compileOnly 'org.projectlombok:lombok'\n"
"        annotationProcessor 'org.projectlombok:lombok'\n"
"    }\n"
"    test { useJUnitPlatform() }\n"
"}\n\n"
"wrapper {\n"
"    gradleVersion = '9.3.0'\n"
"    distributionType = Wrapper.DistributionType.BIN\n"
"}\n")

write("gateway-service/build.gradle",
"plugins {\n"
"    id 'org.springframework.boot'\n"
"    id 'io.spring.dependency-management'\n"
"}\n\n"
"dependencies {\n"
"    implementation 'org.springframework.cloud:spring-cloud-starter-gateway'\n"
"    implementation 'org.springframework.boot:spring-boot-starter-actuator'\n"
"    implementation 'org.springframework.kafka:spring-kafka'\n"
"    implementation 'io.micrometer:micrometer-tracing-bridge-otel'\n"
"    implementation 'io.opentelemetry:opentelemetry-exporter-otlp'\n"
"    implementation 'net.logstash.logback:logstash-logback-encoder:8.0'\n"
"    testImplementation 'org.springframework.boot:spring-boot-starter-test'\n"
"    testImplementation 'org.springframework.kafka:spring-kafka-test'\n"
"    testImplementation 'io.projectreactor:reactor-test'\n"
"}\n\n"
"dependencyManagement {\n"
"    imports {\n"
"        mavenBom \"org.springframework.cloud:spring-cloud-dependencies:2024.0.1\"\n"
"    }\n"
"}\n")

write("analytics-service/build.gradle",
"plugins {\n"
"    id 'org.springframework.boot'\n"
"    id 'io.spring.dependency-management'\n"
"}\n\n"
"dependencies {\n"
"    implementation 'org.springframework.boot:spring-boot-starter-web'\n"
"    implementation 'org.springframework.boot:spring-boot-starter-actuator'\n"
"    implementation 'org.springframework.boot:spring-boot-starter-data-elasticsearch'\n"
"    implementation 'org.springframework.kafka:spring-kafka'\n"
"    implementation 'io.micrometer:micrometer-tracing-bridge-otel'\n"
"    implementation 'io.opentelemetry:opentelemetry-exporter-otlp'\n"
"    implementation 'net.logstash.logback:logstash-logback-encoder:8.0'\n"
"    testImplementation 'org.springframework.boot:spring-boot-starter-test'\n"
"    testImplementation 'org.springframework.kafka:spring-kafka-test'\n"
"}\n")

write("alert-service/build.gradle",
"plugins {\n"
"    id 'org.springframework.boot'\n"
"    id 'io.spring.dependency-management'\n"
"}\n\n"
"dependencies {\n"
"    implementation 'org.springframework.boot:spring-boot-starter-web'\n"
"    implementation 'org.springframework.boot:spring-boot-starter-actuator'\n"
"    implementation 'org.springframework.boot:spring-boot-starter-mail'\n"
"    implementation 'org.springframework.kafka:spring-kafka'\n"
"    implementation 'io.micrometer:micrometer-tracing-bridge-otel'\n"
"    implementation 'io.opentelemetry:opentelemetry-exporter-otlp'\n"
"    implementation 'net.logstash.logback:logstash-logback-encoder:8.0'\n"
"    testImplementation 'org.springframework.boot:spring-boot-starter-test'\n"
"    testImplementation 'org.springframework.kafka:spring-kafka-test'\n"
"}\n")

print("Done - updated for Spring Boot 3.4.4 + Gradle 9.3.0 + Java 25")

