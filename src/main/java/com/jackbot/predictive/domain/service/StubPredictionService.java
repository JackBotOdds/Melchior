package com.jackbot.predictive.domain.service;

import com.jackbot.predictive.application.dto.*;
import com.jackbot.predictive.domain.model.PredictionType;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Service;

@Service
@Profile("dev")   // nunca sobe em prod — CA-1.3.4
public class StubPredictionService implements IPredictionService {

    @Value("${prediction.stub-model-version}")
    private String modelVersion;

    //region --- Constants for Stub Data ---
    private static final double MATCH_OUTCOME_CONFIDENCE = 0.75;
    private static final double MATCH_OUTCOME_HOME_WIN_PROB = 0.75;
    private static final double MATCH_OUTCOME_DRAW_PROB = 0.15;
    private static final double MATCH_OUTCOME_AWAY_WIN_PROB = 0.10;

    private static final double TEAM_SOG_CONFIDENCE = 0.70;
    private static final double TEAM_SOG_HOME_EXPECTED = 5.2;
    private static final double TEAM_SOG_AWAY_EXPECTED = 3.8;

    private static final double TOTAL_GOALS_CONFIDENCE = 0.68;
    private static final double TOTAL_GOALS_EXPECTED = 2.6;
    private static final double TOTAL_GOALS_OVER_2_5_PROB = 0.61;
    private static final double TOTAL_GOALS_OVER_3_5_PROB = 0.32;

    private static final double BTTS_CONFIDENCE = 0.72;
    private static final double BTTS_YES_PROB = 0.58;
    private static final double BTTS_NO_PROB = 0.31;

    private static final double CORNER_COUNT_CONFIDENCE = 0.65;
    private static final double CORNER_COUNT_EXPECTED = 10.4;
    private static final double CORNER_COUNT_OVER_9_5_PROB = 0.55;

    private static final double PLAYER_PERF_CONFIDENCE = 0.60;
    private static final double PLAYER_PERF_SCORE_PROB = 0.34;
    private static final double PLAYER_PERF_ASSIST_PROB = 0.22;
    private static final double PLAYER_PERF_FANTASY_SCORE = 7.8;
    //endregion

    @Override
    public PredictionResponseDTO getMatchOutcome(String matchId) {
        return PredictionResponseDTO.of(
            PredictionType.MATCH_OUTCOME,
            MATCH_OUTCOME_CONFIDENCE,
            modelVersion,
            new MatchOutcomePredictionData(MATCH_OUTCOME_HOME_WIN_PROB, MATCH_OUTCOME_DRAW_PROB, MATCH_OUTCOME_AWAY_WIN_PROB)
        );
    }

    @Override
    public PredictionResponseDTO getTeamShotsOnGoal(String matchId) {
        return PredictionResponseDTO.of(
            PredictionType.TEAM_SOG,
            TEAM_SOG_CONFIDENCE,
            modelVersion,
            new TeamSogPredictionData(TEAM_SOG_HOME_EXPECTED, TEAM_SOG_AWAY_EXPECTED)
        );
    }

    @Override
    public PredictionResponseDTO getTotalGoals(String matchId) {
        return PredictionResponseDTO.of(
            PredictionType.TOTAL_GOALS,
            TOTAL_GOALS_CONFIDENCE,
            modelVersion,
            new TotalGoalsPredictionData(TOTAL_GOALS_EXPECTED, TOTAL_GOALS_OVER_2_5_PROB, TOTAL_GOALS_OVER_3_5_PROB)
        );
    }

    @Override
    public PredictionResponseDTO getBothTeamsToScore(String matchId) {
        return PredictionResponseDTO.of(
            PredictionType.BTTS,
            BTTS_CONFIDENCE,
            modelVersion,
            new BttsPredictionData(BTTS_YES_PROB, BTTS_NO_PROB)
        );
    }

    @Override
    public PredictionResponseDTO getCornerCount(String matchId) {
        return PredictionResponseDTO.of(
            PredictionType.CORNER_COUNT,
            CORNER_COUNT_CONFIDENCE,
            modelVersion,
            new CornerCountPredictionData(CORNER_COUNT_EXPECTED, CORNER_COUNT_OVER_9_5_PROB)
        );
    }

    @Override
    public PredictionResponseDTO getPlayerPerformance(String matchId) {
        return PredictionResponseDTO.of(
            PredictionType.PLAYER_PERFORMANCE,
            PLAYER_PERF_CONFIDENCE,
            modelVersion,
            new PlayerPerformancePredictionData(PLAYER_PERF_SCORE_PROB, PLAYER_PERF_ASSIST_PROB, PLAYER_PERF_FANTASY_SCORE)
        );
    }
}
