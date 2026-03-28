# JackBot Prediction Service API Documentation

This document details the API for the JackBot Prediction Service, which provides sports betting predictions. This service is part of the Melchior team's responsibility and is currently in Sprint 1, meaning it uses stubbed data.

## Base URL

The base URL for the API is determined by the `PREDICTIVE_PORT` environment variable. If not set, it defaults to `8080`.
Example: `http://localhost:8080/api/v1/predictions`

## Authentication

For Sprint 1, authentication is largely disabled for `dev` and `test` profiles.
- **`dev` profile**: All routes are accessible without authentication, including Swagger UI and Actuator endpoints.
- **`test` profile**: Only Actuator health endpoints (`/actuator/health`, `/actuator/info`) are accessible. All other routes are denied.
- **`prod` profile (default)**: Only Actuator health endpoints are accessible without authentication. All other routes require authentication (JWT authentication will be added in Sprint 2).

**Note**: No specific headers for authentication are required in Sprint 1 for the `dev` profile.

## Endpoints

All prediction endpoints require a `matchId` as a query parameter. The `matchId` must adhere to the pattern `^[a-zA-Z0-9\\-]{3,50}$` (letters, numbers, and hyphens, 3-50 characters).

### 1. Get Match Outcome Prediction

**GET** `/api/v1/predictions/match-outcome`

*   **Description**: Returns probabilities for home win, draw, and away win for a given match.
*   **Query Parameters**:
    *   `matchId` (string, **required**): Unique identifier for the match.
        *   Example: `match-2025-bra-arg-001`
*   **Response (200 OK)**: `PredictionResponseDTO` with `data` as `MatchOutcomePredictionData`.

    ```json
    {
      "predictionType": "MATCH_OUTCOME",
      "confidenceScore": 0.82,
      "modelVersion": "stub-v1.0",
      "generatedAt": "2025-01-01T00:00:00Z",
      "data": {
        "homeWinProbability": 0.75,
        "drawProbability": 0.15,
        "awayWinProbability": 0.10
      }
    }
    ```

### 2. Get Team Shots On Goal Prediction

**GET** `/api/v1/predictions/team-sog`

*   **Description**: Estimates expected shots on goal for both home and away teams.
*   **Query Parameters**:
    *   `matchId` (string, **required**): Unique identifier for the match.
        *   Example: `match-2025-bra-arg-001`
*   **Response (200 OK)**: `PredictionResponseDTO` with `data` as `TeamSogPredictionData`.

    ```json
    {
      "predictionType": "TEAM_SOG",
      "confidenceScore": 0.82,
      "modelVersion": "stub-v1.0",
      "generatedAt": "2025-01-01T00:00:00Z",
      "data": {
        "homeShotsOnGoal": 5.2,
        "awayShotsOnGoal": 3.8
      }
    }
    ```

### 3. Get Total Goals Prediction

**GET** `/api/v1/predictions/total-goals`

*   **Description**: Estimates expected goals (xG) and probabilities for over/under total goals.
*   **Query Parameters**:
    *   `matchId` (string, **required**): Unique identifier for the match.
        *   Example: `match-2025-bra-arg-001`
*   **Response (200 OK)**: `PredictionResponseDTO` with `data` as `TotalGoalsPredictionData`.

    ```json
    {
      "predictionType": "TOTAL_GOALS",
      "confidenceScore": 0.82,
      "modelVersion": "stub-v1.0",
      "generatedAt": "2025-01-01T00:00:00Z",
      "data": {
        "expectedGoals": 2.6,
        "over25Probability": 0.61,
        "over35Probability": 0.32
      }
    }
    ```

### 4. Get Both Teams To Score (BTTS) Prediction

**GET** `/api/v1/predictions/btts`

*   **Description**: Returns the probability of both teams scoring in the match.
*   **Query Parameters**:
    *   `matchId` (string, **required**): Unique identifier for the match.
        *   Example: `match-2025-bra-arg-001`
*   **Response (200 OK)**: `PredictionResponseDTO` with `data` as `BttsPredictionData`.

    ```json
    {
      "predictionType": "BTTS",
      "confidenceScore": 0.82,
      "modelVersion": "stub-v1.0",
      "generatedAt": "2025-01-01T00:00:00Z",
      "data": {
        "bttsProbability": 0.58,
        "oneTeamOnlyProbability": 0.31
      }
    }
    ```

### 5. Get Corner Count Prediction

**GET** `/api/v1/predictions/corner-count`

*   **Description**: Estimates the total expected corners and over/under probabilities.
*   **Query Parameters**:
    *   `matchId` (string, **required**): Unique identifier for the match.
        *   Example: `match-2025-bra-arg-001`
*   **Response (200 OK)**: `PredictionResponseDTO` with `data` as `CornerCountPredictionData`.

    ```json
    {
      "predictionType": "CORNER_COUNT",
      "confidenceScore": 0.82,
      "modelVersion": "stub-v1.0",
      "generatedAt": "2025-01-01T00:00:00Z",
      "data": {
        "expectedCorners": 10.4,
        "over9_5Probability": 0.55
      }
    }
    ```

### 6. Get Player Performance Prediction

**GET** `/api/v1/predictions/player-performance`

*   **Description**: Provides expected performance metrics for a player, including score probability, assist probability, and expected fantasy score.
*   **Query Parameters**:
    *   `matchId` (string, **required**): Unique identifier for the match.
        *   Example: `match-2025-bra-arg-001`
*   **Response (200 OK)**: `PredictionResponseDTO` with `data` as `PlayerPerformancePredictionData`.

    ```json
    {
      "predictionType": "PLAYER_PERFORMANCE",
      "confidenceScore": 0.82,
      "modelVersion": "stub-v1.0",
      "generatedAt": "2025-01-01T00:00:00Z",
      "data": {
        "scoreProbability": 0.34,
        "assistProbability": 0.22,
        "expectedFantasyScore": 7.8
      }
    }
    ```

## Common Response Structure (`PredictionResponseDTO`)

All successful prediction responses are wrapped in a `PredictionResponseDTO`.

*   `predictionType` (string): The type of prediction (e.g., `MATCH_OUTCOME`, `BTTS`). See `PredictionType.java` for possible values.
*   `confidenceScore` (double): A score from 0.0 to 1.0 indicating the model's confidence in the prediction.
*   `modelVersion` (string): The version of the model used to generate the prediction.
*   `generatedAt` (string, ISO-8601): Timestamp when the prediction was generated.
*   `data` (object): Contains the specific prediction data, whose structure varies based on `predictionType`.

## Error Response Structure (`ErrorResponseDTO`)

When an error occurs (e.g., invalid `matchId`), the API returns an `ErrorResponseDTO`.

```json
{
  "status": 400,
  "error": "Bad Request",
  "details": "matchId must contain only letters, numbers and hyphens (3–50 characters)",
  "timestamp": "2025-01-01T00:00:00Z"
}
```

## Environment Variables

The following environment variables are used to configure the Prediction Service:

*   `PREDICTIVE_PORT` (optional): The port on which the service will run.
    *   Default: `8080`
    *   Example: `PREDICTIVE_PORT=8081`
*   `SPRING_PROFILES_ACTIVE` (optional): Specifies the active Spring profile. This affects security configurations and other profile-specific beans.
    *   Default: `dev`
    *   Possible values: `dev`, `test`, `prod`
    *   Example: `SPRING_PROFILES_ACTIVE=prod`
*   `CORS_ALLOWED_ORIGINS` (optional): A comma-separated list of origins allowed to make cross-origin requests to the API.
    *   Default: `http://localhost:5173`
    *   Example: `CORS_ALLOWED_ORIGINS=http://localhost:3000,https://your-frontend.com`

## CORS Configuration

The API is configured to handle Cross-Origin Resource Sharing (CORS).
- **Allowed Origins**: Configured via `CORS_ALLOWED_ORIGINS` environment variable.
- **Allowed Methods**: `GET`, `POST`, `PUT`, `DELETE`, `PATCH`, `OPTIONS`.
- **Allowed Headers**: All headers (`*`).
- **Allow Credentials**: `true`.
- **Max Age**: `3600` seconds.

## Swagger UI

The API documentation is available via Swagger UI at `/swagger-ui.html` when the `dev` profile is active.
The OpenAPI specification can be accessed at `/v3/api-docs`.
