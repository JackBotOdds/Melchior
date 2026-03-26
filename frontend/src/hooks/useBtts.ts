import { usePrediction } from './usePrediction';
import type { BttsPredictionData } from '../types/predictions';

/**
 * Hook to fetch predictions for Both Teams to Score (BTTS).
 * @param matchId The ID of the match.
 * @param sessionId The session ID for tracking/authentication.
 */
export function useBtts(matchId: string | null, sessionId: string | null) {
  return usePrediction<BttsPredictionData>(
    '/predictions/btts',
    matchId,
    sessionId
  );
}
