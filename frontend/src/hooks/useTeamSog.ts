import { usePrediction } from './usePrediction';
import type { TeamSogPredictionData } from '../types/predictions';

/**
 * Hook to fetch predictions for Team Shots on Goal.
 * @param matchId The ID of the match.
 * @param sessionId The session ID for tracking/authentication.
 */
export function useTeamSog(matchId: string | null, sessionId: string | null) {
  return usePrediction<TeamSogPredictionData>(
    '/predictions/team-sog',
    matchId,
    sessionId
  );
}
