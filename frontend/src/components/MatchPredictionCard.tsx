import { useState } from 'react';
import type { FC } from 'react';
import { PredictionTypeValues } from '../types/predictions';
import type { AnyPredictionResponse } from '../types/predictions';

interface Props {
  title: string;
  prediction: AnyPredictionResponse | null;
  isLoading: boolean;
}

const renderPredictionData = (prediction: AnyPredictionResponse, isExpanded: boolean) => {
  switch (prediction.predictionType) {
    case PredictionTypeValues.MATCH_OUTCOME:
      return (
        <>
          <p><strong>Home Win:</strong> {(prediction.data.homeWinProbability * 100).toFixed(0)}%</p>
          <p><strong>Draw:</strong> {(prediction.data.drawProbability * 100).toFixed(0)}%</p>
          <p><strong>Away Win:</strong> {(prediction.data.awayWinProbability * 100).toFixed(0)}%</p>
        </>
      );
    case PredictionTypeValues.TOTAL_GOALS:
      return (
        <>
          <p><strong>Expected Goals (xG):</strong> {prediction.data.expectedGoals.toFixed(2)}</p>
          <p><strong>Over 2.5 Goals:</strong> {(prediction.data.over25Probability * 100).toFixed(0)}%</p>
          {isExpanded && <p><strong>Over 3.5 Goals:</strong> {(prediction.data.over35Probability * 100).toFixed(0)}%</p>}
        </>
      );
    case PredictionTypeValues.BTTS:
      return (
        <>
          <p><strong>Yes:</strong> {(prediction.data.bttsProbability * 100).toFixed(0)}%</p>
          {isExpanded && <p><strong>No:</strong> {(prediction.data.oneTeamOnlyProbability * 100).toFixed(0)}%</p>}
        </>
      );
    case PredictionTypeValues.CORNER_COUNT:
        return (
            <>
                <p><strong>Expected Corners:</strong> {prediction.data.expectedCorners.toFixed(2)}</p>
                <p><strong>Over 9.5 Corners:</strong> {(prediction.data.over9_5Probability * 100).toFixed(0)}%</p>
            </>
        );
    case PredictionTypeValues.TEAM_SOG:
        return (
            <>
                <p><strong>Home Shots on Goal:</strong> {prediction.data.homeShotsOnGoal.toFixed(2)}</p>
                <p><strong>Away Shots on Goal:</strong> {prediction.data.awayShotsOnGoal.toFixed(2)}</p>
            </>
        );
    case PredictionTypeValues.PLAYER_PERFORMANCE:
        return (
            <>
                <p><strong>Expected Fantasy Score:</strong> {prediction.data.expectedFantasyScore.toFixed(2)}</p>
                <p><strong>Score Probability:</strong> {(prediction.data.scoreProbability * 100).toFixed(0)}%</p>
                <p><strong>Assist Probability:</strong> {(prediction.data.assistProbability * 100).toFixed(0)}%</p>
            </>
        );
    default:
      return <p>Prediction data format not recognized.</p>;
  }
};

export const MatchPredictionCard: FC<Props> = ({ title, prediction, isLoading }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const handleCardClick = () => {
    if (prediction) {
      setIsExpanded(!isExpanded);
    }
  };

  const cardClassName = `prediction-card ${prediction ? 'clickable' : ''} ${isExpanded ? 'expanded' : ''}`;

  return (
    <div className={cardClassName} onClick={handleCardClick}>
      <h2>{title}</h2>
      {isLoading && <div className="loading">Analisando dados...</div>}
      {prediction && (
        <div className="content">
          <p><strong>Confidence:</strong> {prediction.confidenceScore.toFixed(2)}</p>
          {renderPredictionData(prediction, isExpanded)}
        </div>
      )}
    </div>
  );
};
