package com.jackbot.predictive.domain.service;

import com.jackbot.predictive.application.dto.PredictionResponseDTO;
import com.jackbot.predictive.domain.model.PredictionType;
import com.jackbot.predictive.infrastructure.caspar.CasparClient;
import io.github.resilience4j.circuitbreaker.annotation.CircuitBreaker;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.context.annotation.Primary;
import org.springframework.stereotype.Service;

@Slf4j
@Service
@Primary
@RequiredArgsConstructor
public class CasparPredictionService implements IPredictionService {

    private final CasparClient casparClient;
    private final StubPredictionService stubService;

    @Override
    @CircuitBreaker(name = "caspar", fallbackMethod = "getMatchOutcomeFallback")
    public PredictionResponseDTO getMatchOutcome(String matchId) {
        var response = casparClient.getMatchOutcome(matchId);
        return PredictionResponseDTO.of(
            PredictionType.MATCH_OUTCOME,
            response.confidence(),
            response.version(),
            response.data()
        );
    }

    public PredictionResponseDTO getMatchOutcomeFallback(String matchId, Throwable t) {
        log.warn("Fallback triggered for match-outcome (matchId: {}): {}", matchId, t.getMessage());
        return stubService.getMatchOutcome(matchId);
    }

    @Override
    @CircuitBreaker(name = "caspar", fallbackMethod = "getTotalGoalsFallback")
    public PredictionResponseDTO getTotalGoals(String matchId) {
        var response = casparClient.getTotalGoals(matchId);
        return PredictionResponseDTO.of(
            PredictionType.TOTAL_GOALS,
            response.confidence(),
            response.version(),
            response.data()
        );
    }

    public PredictionResponseDTO getTotalGoalsFallback(String matchId, Throwable t) {
        log.warn("Fallback triggered for total-goals (matchId: {}): {}", matchId, t.getMessage());
        return stubService.getTotalGoals(matchId);
    }

    @Override
    @CircuitBreaker(name = "caspar", fallbackMethod = "getBothTeamsToScoreFallback")
    public PredictionResponseDTO getBothTeamsToScore(String matchId) {
        var response = casparClient.getBtts(matchId);
        return PredictionResponseDTO.of(
            PredictionType.BTTS,
            response.confidence(),
            response.version(),
            response.data()
        );
    }

    public PredictionResponseDTO getBothTeamsToScoreFallback(String matchId, Throwable t) {
        log.warn("Fallback triggered for btts (matchId: {}): {}", matchId, t.getMessage());
        return stubService.getBothTeamsToScore(matchId);
    }

    @Override
    public PredictionResponseDTO getTeamShotsOnGoal(String matchId) {
        return stubService.getTeamShotsOnGoal(matchId);
    }

    @Override
    public PredictionResponseDTO getCornerCount(String matchId) {
        return stubService.getCornerCount(matchId);
    }

    @Override
    public PredictionResponseDTO getPlayerPerformance(String matchId) {
        return stubService.getPlayerPerformance(matchId);
    }
}
