package com.jackbot.predictive.infrastructure.web.controller;

import com.jackbot.predictive.application.dto.ErrorResponseDTO;
import jakarta.validation.ConstraintViolationException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.MissingServletRequestParameterException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import java.time.Instant;
import java.util.stream.Collectors;

@RestControllerAdvice
public class GlobalExceptionHandler {

    /** Parâmetros de query com @Validated no controller (@NotBlank, @Pattern) */
    @ExceptionHandler(ConstraintViolationException.class)
    public ResponseEntity<ErrorResponseDTO> handleConstraint(ConstraintViolationException ex) {
        String details = ex.getConstraintViolations().stream()
            .map(v -> v.getPropertyPath() + ": " + v.getMessage())
            .collect(Collectors.joining("; "));

        return bad("Parâmetro inválido", details);
    }

    /** @RequestBody com @Valid — usado em outros endpoints do sistema */
    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ErrorResponseDTO> handleBodyValidation(MethodArgumentNotValidException ex) {
        String details = ex.getBindingResult().getFieldErrors().stream()
            .map(e -> e.getField() + ": " + e.getDefaultMessage())
            .collect(Collectors.joining("; "));

        return bad("Payload inválido", details);
    }

    /** @RequestParam obrigatório ausente na URL */
    @ExceptionHandler(MissingServletRequestParameterException.class)
    public ResponseEntity<ErrorResponseDTO> handleMissingParam(MissingServletRequestParameterException ex) {
        return bad("Parâmetro obrigatório ausente", "O parâmetro '" + ex.getParameterName() + "' é obrigatório");
    }

    /** Fallback para exceções não tratadas */
    @ExceptionHandler(Exception.class)
    public ResponseEntity<ErrorResponseDTO> handleGeneric(Exception ex) {
        return ResponseEntity
            .status(HttpStatus.INTERNAL_SERVER_ERROR)
            .body(new ErrorResponseDTO(500, "Erro interno", "Contate o suporte técnico", Instant.now().toString()));
    }

    private ResponseEntity<ErrorResponseDTO> bad(String error, String details) {
        return ResponseEntity
            .status(HttpStatus.BAD_REQUEST)
            .body(new ErrorResponseDTO(400, error, details, Instant.now().toString()));
    }
}
