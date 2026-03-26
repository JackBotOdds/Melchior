import './App.css';
import { MatchPredictionCard } from './components/MatchPredictionCard';
import { PredictionError } from './components/common/PredictionError';
import { useBtts } from './hooks/useBtts';
import { useCornerCount } from './hooks/useCornerCount';
import { useMatchOutcome } from './hooks/useMatchOutcome';
import { usePlayerPerformance } from './hooks/usePlayerPerformance';
import { useSessionId } from './hooks/useSessionId';
import { useTeamSog } from './hooks/useTeamSog';
import { useTotalGoals } from './hooks/useTotalGoals';
import type { AnyPredictionResponse } from './types/predictions';

function App() {
  const sessionId = useSessionId();
  const matchId = 'match-2025-bra-arg-001'; // Example matchId

  const { data: matchOutcome, isLoading: loadingMatchOutcome, error: errorMatchOutcome } = useMatchOutcome(matchId, sessionId);
  const { data: totalGoals, isLoading: loadingTotalGoals, error: errorTotalGoals } = useTotalGoals(matchId, sessionId);
  const { data: btts, isLoading: loadingBtts, error: errorBtts } = useBtts(matchId, sessionId);
  const { data: cornerCount, isLoading: loadingCornerCount, error: errorCornerCount } = useCornerCount(matchId, sessionId);
  const { data: teamSog, isLoading: loadingTeamSog, error: errorTeamSog } = useTeamSog(matchId, sessionId);
  const { data: playerPerformance, isLoading: loadingPlayerPerformance, error: errorPlayerPerformance } = usePlayerPerformance(matchId, sessionId);

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>JackBot: Predictive Analytics</h1>
        <p>Session ID: {sessionId}</p>
      </header>
      <main className="predictions-grid">
        {errorMatchOutcome ? <PredictionError error={errorMatchOutcome} /> : <MatchPredictionCard title="Match Outcome" prediction={matchOutcome as AnyPredictionResponse | null} isLoading={loadingMatchOutcome} />}
        {errorTotalGoals ? <PredictionError error={errorTotalGoals} /> : <MatchPredictionCard title="Total Goals" prediction={totalGoals as AnyPredictionResponse | null} isLoading={loadingTotalGoals} />}
        {errorBtts ? <PredictionError error={errorBtts} /> : <MatchPredictionCard title="Both Teams to Score" prediction={btts as AnyPredictionResponse | null} isLoading={loadingBtts} />}
        {errorCornerCount ? <PredictionError error={errorCornerCount} /> : <MatchPredictionCard title="Corner Count" prediction={cornerCount as AnyPredictionResponse | null} isLoading={loadingCornerCount} />}
        {errorTeamSog ? <PredictionError error={errorTeamSog} /> : <MatchPredictionCard title="Team Shots on Goal" prediction={teamSog as AnyPredictionResponse | null} isLoading={loadingTeamSog} />}
        {errorPlayerPerformance ? <PredictionError error={errorPlayerPerformance} /> : <MatchPredictionCard title="Player Performance" prediction={playerPerformance as AnyPredictionResponse | null} isLoading={loadingPlayerPerformance} />}
      </main>
    </div>
  );
}

export default App;

