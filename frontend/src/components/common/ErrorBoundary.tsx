import { Component } from 'react';
import type { ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
}

/**
 * A classic React Error Boundary component that catches JavaScript errors
 * in its child component tree, logs those errors, and displays a
 * fallback UI instead of a crashed component tree.
 */
export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
  };

  public static getDerivedStateFromError(_: Error): State {
    // Update state so the next render will show the fallback UI.
    return { hasError: true };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // You can also log the error to an error reporting service here
    console.error("Uncaught error:", error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      // You can render any custom fallback UI
      return (
        <div className="prediction-error">
          <h4>Ocorreu um Problema</h4>
          <p>Algo deu errado ao exibir esta informação. Por favor, atualize a página.</p>
        </div>
      );
    }

    return this.props.children;
  }
}
