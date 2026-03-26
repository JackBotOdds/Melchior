package com.jackbot.predictive.application.dto;

import com.jackbot.predictive.domain.model.PredictionType;
import io.swagger.v3.oas.annotations.media.Schema;
import java.time.Instant;

@Schema(description = "Envelope padrão de resposta do serviço preditivo")
public record PredictionResponseDTO(

    @Schema(description = "Tipo da aposta analisada", example = "MATCH_OUTCOME")
    PredictionType predictionType,

    @Schema(description = "Score de confiança do modelo (0.0–1.0)", example = "0.82")
    double confidenceScore,

    @Schema(description = "Versão do modelo utilizado", example = "stub-v1.0")
    String modelVersion,

    @Schema(description = "Momento de geração da predição (ISO-8601)", example = "2025-01-01T00:00:00Z")
    Instant generatedAt,

    @Schema(description = "Dados específicos do tipo de aposta — estrutura varia conforme predictionType")
    Object data
) {
    /** Factory para simplificar criação nos Services */
    public static PredictionResponseDTO of(PredictionType type, double confidence, String modelVersion, Object data) {
        return new PredictionResponseDTO(
            type,
            confidence,
            modelVersion,
            Instant.now(),
            data
        );
    }
}
