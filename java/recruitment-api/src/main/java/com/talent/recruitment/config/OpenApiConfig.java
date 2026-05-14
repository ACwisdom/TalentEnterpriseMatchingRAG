package com.talent.recruitment.config;

import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Info;

@Configuration
@EnableConfigurationProperties(ServiceProperties.class)
public class OpenApiConfig {

    @Bean
    public OpenAPI recruitmentOpenApi() {
        return new OpenAPI()
                .info(new Info()
                        .title("Recruitment API")
                        .description("v1 REST API for candidates, jobs, recommendations, reminders")
                        .version("v1"));
    }
}
