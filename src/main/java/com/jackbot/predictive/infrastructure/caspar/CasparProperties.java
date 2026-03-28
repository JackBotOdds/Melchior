package com.jackbot.predictive.infrastructure.caspar;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

@Data
@Configuration
@ConfigurationProperties(prefix = "caspar")
public class CasparProperties {
    private String baseUrl;
    private int timeoutSeconds;
}
