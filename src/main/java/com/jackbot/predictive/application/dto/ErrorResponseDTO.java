package com.jackbot.predictive.application.dto;

public record ErrorResponseDTO(int status, String error, String details, String timestamp) {}
