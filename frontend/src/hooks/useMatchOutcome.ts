import { usePrediction } from './usePrediction';
import type { MatchOutcomePredictionData } from '../types/predictions';

/**
 * Hook to fetch predictions for Match Outcome.
 * @param matchId The ID of the match.
 * @param sessionId The session ID for tracking/authentication.
 */
export function useMatchOutcome(matchId: string | null, sessionId: string | null) {
  return usePrediction<MatchOutcomePredictionData>(
    '/predictions/match-outcome',
    matchId,
    sessionId
  );
}
