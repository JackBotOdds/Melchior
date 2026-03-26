import type { PredictionType } from '../types/predictions'; import { PredictionTypeValues } from '../types/predictions';

// Object to centralize texts for easy maintenance and future internationalization.
const confidenceText = {
  high: {
    generic: 'Alta probabilidade',
    [PredictionTypeValues.TOTAL_GOALS]: 'Expectativa de um jogo aberto, com alta probabilidade',
  },
  medium: {
    generic: 'Boa tendência',
    [PredictionTypeValues.TOTAL_GOALS]: 'Expectativa de um jogo equilibrado, com tendência',
  },
  low: {
    generic: 'Chance moderada',
    [PredictionTypeValues.TOTAL_GOALS]: 'Expectativa de um jogo fechado, com chance moderada',
  },
};

/**
 * Formats a numerical probability (0.0 to 1.0) into an educational text.
 *
 * @param value The probability to be formatted (e.g., 0.75).
 * @param context The prediction type, used to adapt the message.
 * @returns A string with the qualitative interpretation of the probability.
 */
export function formatProbabilityToText(
  value: number,
  context: PredictionType
): string {
  let level: 'high' | 'medium' | 'low';

  // CA-1.6.2: High confidence
  if (value >= 0.70) {
    level = 'high';
  // CA-1.6.3: Medium confidence
  } else if (value >= 0.50) {
    level = 'medium';
  // CA-1.6.4: Low confidence
  } else {
    level = 'low';
  }

  // CA-1.6.5: Contextualization logic
  switch (context) {
    case PredictionTypeValues.TOTAL_GOALS:
      return confidenceText[level][PredictionTypeValues.TOTAL_GOALS];
    // Add other specific cases here as needed
    // case PredictionType.BTTS:
    //   return ...
    default:
      return confidenceText[level].generic;
  }
}
