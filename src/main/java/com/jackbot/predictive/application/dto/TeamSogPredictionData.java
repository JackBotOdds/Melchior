package com.jackbot.predictive.application.dto;

import io.swagger.v3.oas.annotations.media.Schema;

public record TeamSogPredictionData(
    @Schema(description = "Chutes a gol esperados — time da casa",  example = "5.2") double homeShotsOnGoal,
    @Schema(description = "Chutes a gol esperados — time visitante", example = "3.8") double awayShotsOnGoal
) {}
