package com.jackbot.predictive.application.dto;

import io.swagger.v3.oas.annotations.media.Schema;

public record BttsPredictionData(
    @Schema(description = "Probabilidade de ambos marcarem", example = "0.58") double bttsProbability,
    @Schema(description = "Probabilidade de apenas um time marcar", example = "0.31") double oneTeamOnlyProbability
) {}
