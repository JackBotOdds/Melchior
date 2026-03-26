package com.jackbot.predictive.application.dto;

import io.swagger.v3.oas.annotations.media.Schema;

public record MatchOutcomePredictionData(
    @Schema(example = "0.75") double homeWinProbability,
    @Schema(example = "0.15") double drawProbability,
    @Schema(example = "0.10") double awayWinProbability
) {}
