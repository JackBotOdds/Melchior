package com.jackbot.predictive.application.dto;

import io.swagger.v3.oas.annotations.media.Schema;

public record PlayerPerformancePredictionData(
    @Schema(description = "Probabilidade de o jogador marcar",           example = "0.34") double scoreProbability,
    @Schema(description = "Probabilidade de o jogador dar assistência",  example = "0.22") double assistProbability,
    @Schema(description = "Pontuação de desempenho esperada (fantasy)",  example = "7.8")  double expectedFantasyScore
) {}
