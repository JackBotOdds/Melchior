package com.jackbot.predictive.infrastructure.web.controller;

import com.jackbot.predictive.application.dto.PredictionResponseDTO;
import com.jackbot.predictive.domain.service.IPredictionService;
import com.jackbot.predictive.infrastructure.web.validation.ValidMatchId;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@Validated
@RestController
@RequestMapping("/api/v1/predictions")
@Tag(name = "Predictions", description = "Motor preditivo de apostas esportivas — Sprint 1: dados stubados")
public class PredictionController {

    private final IPredictionService predictionService;

    public PredictionController(IPredictionService predictionService) {
        this.predictionService = predictionService;
    }

    @GetMapping("/match-outcome")
    @Operation(
        summary = "Predição de resultado da partida",
        description = "Retorna probabilidades de vitória em casa, empate e vitória fora.",
        parameters = @Parameter(name = "matchId", description = "ID da partida", example = "match-2025-bra-arg-001", required = true),
        responses = {
            @ApiResponse(responseCode = "200", description = "Predição gerada com sucesso",
                content = @Content(schema = @Schema(implementation = PredictionResponseDTO.class))),
            @ApiResponse(responseCode = "400", description = "matchId inválido ou ausente")
        }
    )
    public ResponseEntity<PredictionResponseDTO> matchOutcome(@RequestParam @ValidMatchId String matchId) {
        return ResponseEntity.ok(predictionService.getMatchOutcome(matchId));
    }

    @GetMapping("/team-sog")
    @Operation(summary = "Predição de chutes a gol", description = "Estima chutes a gol esperados por time.")
    public ResponseEntity<PredictionResponseDTO> teamSog(@RequestParam @ValidMatchId String matchId) {
        return ResponseEntity.ok(predictionService.getTeamShotsOnGoal(matchId));
    }

    @GetMapping("/total-goals")
    @Operation(summary = "Predição de total de gols", description = "Estima xG e probabilidades de over/under.")
    public ResponseEntity<PredictionResponseDTO> totalGoals(@RequestParam @ValidMatchId String matchId) {
        return ResponseEntity.ok(predictionService.getTotalGoals(matchId));
    }

    @GetMapping("/btts")
    @Operation(summary = "Predição — ambos marcam (BTTS)", description = "Probabilidade de ambos os times marcarem.")
    public ResponseEntity<PredictionResponseDTO> btts(@RequestParam @ValidMatchId String matchId) {
        return ResponseEntity.ok(predictionService.getBothTeamsToScore(matchId));
    }

    @GetMapping("/corner-count")
    @Operation(summary = "Predição de escanteios", description = "Total esperado de escanteios e over/under.")
    public ResponseEntity<PredictionResponseDTO> cornerCount(@RequestParam @ValidMatchId String matchId) {
        return ResponseEntity.ok(predictionService.getCornerCount(matchId));
    }

    @GetMapping("/player-performance")
    @Operation(summary = "Predição de desempenho de jogador", description = "Score esperado e probabilidades de gol e assistência.")
    public ResponseEntity<PredictionResponseDTO> playerPerformance(@RequestParam @ValidMatchId String matchId) {
        return ResponseEntity.ok(predictionService.getPlayerPerformance(matchId));
    }
}