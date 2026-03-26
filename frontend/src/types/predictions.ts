/**
 * Mirrors PredictionType.java from the backend.
 */
export type PredictionType =
  | 'MATCH_OUTCOME'
  | 'TEAM_SOG'
  | 'TOTAL_GOALS'
  | 'BTTS'
  | 'CORNER_COUNT'
  | 'PLAYER_PERFORMANCE';

export const PredictionTypeValues = {
  MATCH_OUTCOME: 'MATCH_OUTCOME',
  TEAM_SOG: 'TEAM_SOG',
  TOTAL_GOALS: 'TOTAL_GOALS',
  BTTS: 'BTTS',
  CORNER_COUNT: 'CORNER_COUNT',
  PLAYER_PERFORMANCE: 'PLAYER_PERFORMANCE',
} as const;

// --- Interfaces for the specific data of each prediction type ---

export interface MatchOutcomePredictionData {
  homeWinProbability: number;
  drawProbability: number;
  awayWinProbability: number;
}

export interface TeamSogPredictionData {
  homeShotsOnGoal: number;
  awayShotsOnGoal: number;
}

export interface TotalGoalsPredictionData {
  expectedGoals: number;
  over25Probability: number;
  over35Probability: number;
}

export interface BttsPredictionData {
  bttsProbability: number;
  oneTeamOnlyProbability: number;
}

export interface CornerCountPredictionData {
  expectedCorners: number;
  over9_5Probability: number;
}

export interface PlayerPerformancePredictionData {
  scoreProbability: number;
  assistProbability: number;
  expectedFantasyScore: number;
}

/**
 * Generic response envelope from the prediction API.
 * @template T The type of the specific prediction data in the `data` field.
 */
export interface PredictionResponse<T> {
  predictionType: PredictionType;
  confidenceScore: number;
  modelVersion: string;
  generatedAt: string; // ISO-8601 string
  data: T;
}

// Discriminated union for all possible prediction responses
export type AnyPredictionResponse =
  | (Omit<PredictionResponse<MatchOutcomePredictionData>, 'predictionType'> & { predictionType: typeof PredictionTypeValues.MATCH_OUTCOME })
  | (Omit<PredictionResponse<TeamSogPredictionData>, 'predictionType'> & { predictionType: typeof PredictionTypeValues.TEAM_SOG })
  | (Omit<PredictionResponse<TotalGoalsPredictionData>, 'predictionType'> & { predictionType: typeof PredictionTypeValues.TOTAL_GOALS })
  | (Omit<PredictionResponse<BttsPredictionData>, 'predictionType'> & { predictionType: typeof PredictionTypeValues.BTTS })
  | (Omit<PredictionResponse<CornerCountPredictionData>, 'predictionType'> & { predictionType: typeof PredictionTypeValues.CORNER_COUNT })
  | (Omit<PredictionResponse<PlayerPerformancePredictionData>, 'predictionType'> & { predictionType: typeof PredictionTypeValues.PLAYER_PERFORMANCE });
