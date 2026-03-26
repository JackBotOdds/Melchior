import { usePrediction } from './usePrediction';
import type { CornerCountPredictionData } from '../types/predictions';

/**
 * Hook to fetch predictions for Corner Count.
 * @param matchId The ID of the match.
 * @param sessionId The session ID for tracking/authentication.
 */
export function useCornerCount(matchId: string | null, sessionId: string | null) {
  return usePrediction<CornerCountPredictionData>(
    '/predictions/corner-count',
    matchId,
    sessionId
  );
}
