package com.jackbot.predictive.domain.model;

import io.swagger.v3.oas.annotations.media.Schema;

@Schema(description = "Categoria de aposta suportada pelo motor preditivo")
public enum PredictionType {
    MATCH_OUTCOME,       // resultado da partida (vitória casa/fora/empate)
    TEAM_SOG,            // chutes a gol por time
    TOTAL_GOALS,         // total de gols esperados
    BTTS,                // ambos os times marcam
    CORNER_COUNT,        // total de escanteios
    PLAYER_PERFORMANCE   // desempenho individual de jogador
}
