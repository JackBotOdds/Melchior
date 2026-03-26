import { useState, useEffect } from 'react';
import apiClient from '../services/api';
import type { PredictionResponse } from '../types/predictions';

interface UsePredictionState<T> {
  data: PredictionResponse<T> | null;
  isLoading: boolean;
  error: Error | null;
}

/**
 * Generic hook to fetch prediction data from the API.
 * @param endpoint The API path for the prediction (e.g., '/predictions/match-outcome').
 * @param matchId The ID of the match to be analyzed. Can be null to prevent fetching.
 * @param sessionId The session ID for tracking/authentication. Can be null to prevent fetching.
 */
export function usePrediction<T>(
  endpoint: string,
  matchId: string | null,
  sessionId: string | null
) {
  const [state, setState] = useState<UsePredictionState<T>>({
    data: null,
    isLoading: false,
    error: null,
  });

  useEffect(() => {
    // Do not fetch if the matchId or sessionId is not provided
    if (!matchId || !sessionId) {
      setState({ data: null, isLoading: false, error: null });
      return;
    }

    // Controller to cancel the request if the component unmounts
    const abortController = new AbortController();

    const fetchData = async () => {
      setState({ data: null, isLoading: true, error: null });
      try {
        const response = await apiClient.get<PredictionResponse<T>>(endpoint, {
          params: { matchId },
          headers: {
            'X-Session-ID': sessionId,
          },
          signal: abortController.signal,
        });
        setState({ data: response.data, isLoading: false, error: null });
      } catch (err: any) {
        // Ignore the error if it's due to request cancellation
        if (err.name === 'CanceledError') {
          return;
        }
        setState({ data: null, isLoading: false, error: err });
      }
    };

    fetchData();

    // Cleanup function that will be called when the component unmounts
    return () => {
      abortController.abort();
    };
  }, [endpoint, matchId, sessionId]); // Re-run the effect if the endpoint, matchId or sessionId change

  return state;
}
