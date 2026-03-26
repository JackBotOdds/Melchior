import { usePrediction } from './usePrediction';
import type { TotalGoalsPredictionData } from '../types/predictions';

/**
 * Hook to fetch predictions for Total Goals.
 * @param matchId The ID of the match.
 * @param sessionId The session ID for tracking/authentication.
 */
export function useTotalGoals(matchId: string | null, sessionId: string | null) {
  return usePrediction<TotalGoalsPredictionData>(
    '/predictions/total-goals',
    matchId,
    sessionId
  );
}
