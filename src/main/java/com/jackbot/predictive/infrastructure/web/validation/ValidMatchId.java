package com.jackbot.predictive.infrastructure.web.validation;

import jakarta.validation.Constraint;
import jakarta.validation.Payload;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

@Target({ElementType.PARAMETER, ElementType.FIELD})
@Retention(RetentionPolicy.RUNTIME)
@Constraint(validatedBy = {})
@NotBlank(message = "matchId não pode ser vazio")
@Pattern(regexp = "^[a-zA-Z0-9\\-]{3,50}$", message = "matchId deve conter apenas letras, números e hífens (3–50 caracteres)")
public @interface ValidMatchId {
    String message() default "matchId inválido";
    Class<?>[] groups() default {};
    Class<? extends Payload>[] payload() default {};
}
