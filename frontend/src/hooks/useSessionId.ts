// This hook manages the session ID.
import { useState } from 'react';

const SESSION_ID_KEY = 'jackbot:session:id';

function generateSessionId(): string {
  return `session_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
}

/**
 * Hook that returns a stable session ID, persisted in sessionStorage.
 */
export function useSessionId(): string {
  const [sessionId] = useState(() => {
    try {
      const existingId = window.sessionStorage.getItem(SESSION_ID_KEY);
      if (existingId) {
        return existingId;
      }
      const newId = generateSessionId();
      window.sessionStorage.setItem(SESSION_ID_KEY, newId);
      return newId;
    } catch (error) {
      // In case of error (e.g., sessionStorage is disabled), generate a volatile ID.
      console.warn("sessionStorage is not available. Using a volatile session ID.");
      return generateSessionId();
    }
  });

  return sessionId;
}
