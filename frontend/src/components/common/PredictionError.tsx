import React from 'react';

interface Props {
  error: Error;
  onRetry?: () => void;
}

/**
 * A reusable component to display a user-friendly message when an API
 * call fails.
 */
export const PredictionError: React.FC<Props> = ({ error, onRetry }) => {
  return (
    <div className="prediction-error">
      <h4>Falha na Análise</h4>
      <p>{error.message || 'Não foi possível carregar os dados da predição no momento.'}</p>
      {onRetry && <button onClick={onRetry}>Tentar Novamente</button>}
    </div>
  );
};
