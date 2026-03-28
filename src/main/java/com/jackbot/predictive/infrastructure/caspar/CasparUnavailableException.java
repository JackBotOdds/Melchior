package com.jackbot.predictive.infrastructure.caspar;

import lombok.Getter;

@Getter
public class CasparUnavailableException extends RuntimeException {
    private final int statusCode;

    public CasparUnavailableException(String message, int statusCode) {
        super(message);
        this.statusCode = statusCode;
    }

    public CasparUnavailableException(String message, int statusCode, Throwable cause) {
        super(message, cause);
        this.statusCode = statusCode;
    }
}
