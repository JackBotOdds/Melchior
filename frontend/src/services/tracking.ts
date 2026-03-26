import type { PredictionType } from '../types/predictions';
import type { TrackingEvent, TrackingReport } from '../types/tracking';

const EVENTS_STORAGE_KEY = 'jackbot:prediction:events';

/**
 * Tracks a prediction card click event.
 * @param type The type of prediction that was clicked.
 * @param sessionId The user's current session ID.
 */
export function trackPredictionClick(type: PredictionType, sessionId: string): void {
  try {
    const event: TrackingEvent = {
      type,
      sessionId,
      timestamp: new Date().toISOString(),
    };

    // CA-1.8.5: Ensures no personally identifiable information is stored.
    const existingEventsRaw = window.localStorage.getItem(EVENTS_STORAGE_KEY);
    const events: TrackingEvent[] = existingEventsRaw ? JSON.parse(existingEventsRaw) : [];

    // CA-1.8.3: Adds the new event without overwriting previous ones.
    events.push(event);

    window.localStorage.setItem(EVENTS_STORAGE_KEY, JSON.stringify(events));
  } catch (error) {
    console.error("Failed to track event:", error);
  }
}

/**
 * Aggregates events from localStorage and generates a count report.
 * @returns An object with the count of events per prediction type.
 */
export function getTrackingReport(): TrackingReport {
  try {
    const existingEventsRaw = window.localStorage.getItem(EVENTS_STORAGE_KEY);
    if (!existingEventsRaw) {
      return {};
    }

    const events: TrackingEvent[] = JSON.parse(existingEventsRaw);

    // CA-1.8.4: Aggregates events and returns the count.
    return events.reduce((report, event) => {
      report[event.type] = (report[event.type] || 0) + 1;
      return report;
    }, {} as TrackingReport);
  } catch (error) {
    console.error("Failed to generate tracking report:", error);
    return {};
  }
}
