package com.jackbot.predictive.domain.service;

import com.jackbot.predictive.application.dto.PredictionResponseDTO;

public interface IPredictionService {
    PredictionResponseDTO getMatchOutcome(String matchId);
    PredictionResponseDTO getTeamShotsOnGoal(String matchId);
    PredictionResponseDTO getTotalGoals(String matchId);
    PredictionResponseDTO getBothTeamsToScore(String matchId);
    PredictionResponseDTO getCornerCount(String matchId);
    PredictionResponseDTO getPlayerPerformance(String matchId);
}
