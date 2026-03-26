package com.jackbot.predictive.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Profile;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.web.SecurityFilterChain;

@Configuration
@EnableWebSecurity
public class SecurityConfig {

    private static final String[] PUBLIC_ACTUATOR = { "/actuator/health", "/actuator/info" };
    private static final String[] PUBLIC_SWAGGER  = { "/swagger-ui/**", "/swagger-ui.html", "/v3/api-docs/**" };

    /**
     * Perfil DEV: Swagger e actuator liberados sem autenticação (CA-1.1.3, CA-1.1.4).
     * Demais rotas também liberadas na Sprint 1 — trocar por .authenticated() na Sprint 2.
     */
    @Bean
    @Profile("dev")
    public SecurityFilterChain devFilterChain(HttpSecurity http) throws Exception {
        return http
            .csrf(AbstractHttpConfigurer::disable)
            .authorizeHttpRequests(auth -> auth
                .requestMatchers(PUBLIC_ACTUATOR).permitAll()
                .requestMatchers(PUBLIC_SWAGGER).permitAll()
                .anyRequest().permitAll()   // Sprint 1: sem auth real
            )
            .build();
    }

    /**
     * Perfil TEST: Swagger bloqueado; apenas actuator/health acessível.
     * Usado pelo CI para evitar que Swagger vaze em pipelines de teste (mitigação do risco CA-1.1.5).
     */
    @Bean
    @Profile("test")
    public SecurityFilterChain testFilterChain(HttpSecurity http) throws Exception {
        return http
            .csrf(AbstractHttpConfigurer::disable)
            .authorizeHttpRequests(auth -> auth
                .requestMatchers(PUBLIC_ACTUATOR).permitAll()
                .anyRequest().denyAll()     // CI nunca acessa rotas de negócio sem intenção
            )
            .build();
    }

    /**
     * Perfil PROD (default): tudo fechado exceto health.
     * Sprint 2 adicionará autenticação JWT aqui.
     */
    @Bean
    @Profile("!dev & !test")
    public SecurityFilterChain prodFilterChain(HttpSecurity http) throws Exception {
        return http
            .csrf(AbstractHttpConfigurer::disable)
            .authorizeHttpRequests(auth -> auth
                .requestMatchers(PUBLIC_ACTUATOR).permitAll()
                .anyRequest().authenticated()
            )
            .build();
    }
}
