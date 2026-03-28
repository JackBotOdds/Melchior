package com.jackbot.predictive.domain.service;

import com.github.tomakehurst.wiremock.client.WireMock;
import com.github.tomakehurst.wiremock.junit5.WireMockTest;
import com.jackbot.predictive.application.dto.MatchOutcomePredictionData;
import com.jackbot.predictive.application.dto.PredictionResponseDTO;
import com.jackbot.predictive.domain.model.PredictionType;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;

import static com.github.tomakehurst.wiremock.client.WireMock.*;
import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest
@ActiveProfiles("test")
@WireMockTest(httpPort = 8081)
public class CasparPredictionServiceTest {

    @Autowired
    private CasparPredictionService casparPredictionService;

    @DynamicPropertySource
    static void configureProperties(DynamicPropertyRegistry registry) {
        registry.add("caspar.base-url", () -> "http://localhost:8081");
    }

    @Test
    void shouldReturnPredictionFromCaspar() {
        // Given
        String matchId = "match-123";
        stubFor(get(urlPathEqualTo("/predict/match-outcome"))
                .withQueryParam("match_id", equalTo(matchId))
                .willReturn(aResponse()
                        .withHeader("Content-Type", "application/json")
                        .withBody("""
                                {
                                    "confidence": 0.85,
                                    "version": "caspar-v2.0",
                                    "data": {
                                        "homeWinProbability": 0.60,
                                        "drawProbability": 0.25,
                                        "awayWinProbability": 0.15
                                    }
                                }
                                """)));

        // When
        PredictionResponseDTO response = casparPredictionService.getMatchOutcome(matchId);

        // Then
        assertEquals(PredictionType.MATCH_OUTCOME, response.predictionType());
        assertEquals(0.85, response.confidenceScore());
        assertEquals("caspar-v2.0", response.modelVersion());
        
        MatchOutcomePredictionData data = (MatchOutcomePredictionData) response.data();
        assertEquals(0.60, data.homeWinProbability());
    }

    @Test
    void shouldFallbackToStubWhenCasparIsDown() {
        // Given
        String matchId = "match-123";
        stubFor(get(urlPathEqualTo("/predict/match-outcome"))
                .willReturn(aResponse().withStatus(500)));

        // When
        PredictionResponseDTO response = casparPredictionService.getMatchOutcome(matchId);

        // Then
        assertEquals(PredictionType.MATCH_OUTCOME, response.predictionType());
        // Stub values from StubPredictionService
        assertEquals(0.75, response.confidenceScore());
        assertEquals("stub-v1.0", response.modelVersion());
    }
}
