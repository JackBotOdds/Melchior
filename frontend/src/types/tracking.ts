import type { PredictionType } from './predictions';

export interface TrackingEvent {
  type: PredictionType;
  timestamp: string; // ISO 8601 format
  sessionId: string;
}

export type TrackingReport = Partial<Record<PredictionType, number>>;
