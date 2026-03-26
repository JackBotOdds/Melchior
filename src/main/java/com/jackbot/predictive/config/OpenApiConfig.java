package com.jackbot.predictive.config;

import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Info;
import io.swagger.v3.oas.models.info.Contact;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class OpenApiConfig {

    @Bean
    public OpenAPI jackBotOpenAPI() {
        return new OpenAPI()
            .info(new Info()
                .title("JackBot — Prediction Service API")
                .description("Motor preditivo de apostas esportivas. Sprint 1: dados stubados.")
                .version("1.0.0-SNAPSHOT")
                .contact(new Contact().name("Dupla 1 — Melchior")));
    }
}
