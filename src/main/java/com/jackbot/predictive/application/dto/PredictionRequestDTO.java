package com.jackbot.predictive.application.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;

@Schema(description = "Parâmetros de consulta para predições")
public record PredictionRequestDTO(

    @NotBlank(message = "matchId não pode ser vazio")
    @Pattern(regexp = "^[a-zA-Z0-9\\-]{3,50}$",
             message = "matchId deve conter apenas letras, números e hífens (3–50 caracteres)")
    @Schema(description = "Identificador único da partida", example = "match-2025-bra-arg-001")
    String matchId
) {}
