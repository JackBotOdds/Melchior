import { usePrediction } from './usePrediction';
import type { PlayerPerformancePredictionData } from '../types/predictions';

/**
 * Hook to fetch predictions for Player Performance.
 * @param matchId The ID of the match.
 * @param sessionId The session ID for tracking/authentication.
 */
export function usePlayerPerformance(matchId: string | null, sessionId: string | null) {
  return usePrediction<PlayerPerformancePredictionData>(
    '/predictions/player-performance',
    matchId,
    sessionId
  );
}
