package com.jackbot.predictive.infrastructure.caspar;

import com.jackbot.predictive.application.dto.BttsPredictionData;
import com.jackbot.predictive.application.dto.MatchOutcomePredictionData;
import com.jackbot.predictive.application.dto.TotalGoalsPredictionData;
import com.jackbot.predictive.domain.model.PredictionType;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.HttpStatusCode;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

import java.util.Map;

@Component
public class CasparClient {

    private final RestClient restClient;

    public CasparClient(CasparProperties properties, RestClient.Builder builder) {
        this.restClient = builder
                .baseUrl(properties.getBaseUrl())
                .build();
    }

    public CasparResponse<MatchOutcomePredictionData> getMatchOutcome(String matchId) {
        return fetchPrediction(matchId, PredictionType.MATCH_OUTCOME, new ParameterizedTypeReference<CasparResponse<MatchOutcomePredictionData>>() {});
    }

    public CasparResponse<TotalGoalsPredictionData> getTotalGoals(String matchId) {
        return fetchPrediction(matchId, PredictionType.TOTAL_GOALS, new ParameterizedTypeReference<CasparResponse<TotalGoalsPredictionData>>() {});
    }

    public CasparResponse<BttsPredictionData> getBtts(String matchId) {
        return fetchPrediction(matchId, PredictionType.BTTS, new ParameterizedTypeReference<CasparResponse<BttsPredictionData>>() {});
    }

    private <T> CasparResponse<T> fetchPrediction(String matchId, PredictionType type, ParameterizedTypeReference<CasparResponse<T>> responseType) {
        String endpoint = getEndpoint(type);
        return restClient.get()
                .uri(uriBuilder -> uriBuilder
                        .path(endpoint)
                        .queryParam("match_id", matchId)
                        .build())
                .retrieve()
                .onStatus(HttpStatusCode::isError, (request, response) -> {
                    throw new CasparUnavailableException(
                            "Caspar service error: " + response.getStatusText(),
                            response.getStatusCode().value()
                    );
                })
                .body(responseType);
    }

    private String getEndpoint(PredictionType type) {
        return switch (type) {
            case MATCH_OUTCOME -> "/predict/match-outcome";
            case TOTAL_GOALS -> "/predict/total-goals";
            case BTTS -> "/predict/btts";
            default -> throw new IllegalArgumentException("Unsupported prediction type for Caspar: " + type);
        };
    }

    public record CasparResponse<T>(
            double confidence,
            String version,
            T data
    ) {}
}
