package com.jackbot.predictive.application.dto;

import io.swagger.v3.oas.annotations.media.Schema;

public record TotalGoalsPredictionData(
    @Schema(description = "Total de gols esperados (xG)",           example = "2.6")  double expectedGoals,
    @Schema(description = "Probabilidade de mais de 2.5 gols",      example = "0.61") double over25Probability,
    @Schema(description = "Probabilidade de mais de 3.5 gols",      example = "0.32") double over35Probability
) {}
