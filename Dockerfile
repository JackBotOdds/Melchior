FROM eclipse-temurin:21-jdk-alpine AS builder
WORKDIR /build
COPY pom.xml .
COPY .mvn/ .mvn/
COPY mvnw .
RUN sed -i 's/\r$//' ./mvnw
RUN chmod +x ./mvnw
RUN MVNW_VERBOSE=true ./mvnw dependency:go-offline -q
COPY src/ src/
RUN ./mvnw package -DskipTests -q

FROM eclipse-temurin:21-jre-alpine AS runtime
WORKDIR /app
RUN apk --no-cache add curl && \
    addgroup -S jackbot && \
    adduser -S jackbot -G jackbot
USER jackbot
COPY --from=builder /build/target/*.jar app.jar
ENV SERVER_PORT=8080
ENV SPRING_PROFILES_ACTIVE=dev
EXPOSE 8080
ENTRYPOINT ["java",   "-XX:+UseContainerSupport",   "-XX:MaxRAMPercentage=75.0",   "-Djava.security.egd=file:/dev/./urandom",   "-jar", "app.jar"]