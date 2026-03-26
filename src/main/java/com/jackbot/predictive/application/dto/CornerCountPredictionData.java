package com.jackbot.predictive.application.dto;

import io.swagger.v3.oas.annotations.media.Schema;

public record CornerCountPredictionData(
    @Schema(description = "Total de escanteios esperados",        example = "10.4") double expectedCorners,
    @Schema(description = "Probabilidade de mais de 9.5 escanteios", example = "0.55") double over9_5Probability
) {}
