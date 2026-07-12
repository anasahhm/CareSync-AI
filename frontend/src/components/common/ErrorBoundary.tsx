"use client";

import React from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

interface ErrorBoundaryProps {
  children: React.ReactNode;
  /** Short label so a nested boundary's fallback can say what broke (e.g. "Vision panel") */
  section?: string;
  /** Custom fallback renderer; receives the error and a reset function */
  fallback?: (error: Error, reset: () => void) => React.ReactNode;
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
}

interface ErrorBoundaryState {
  error: Error | null;
}

export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error(`ErrorBoundary${this.props.section ? ` (${this.props.section})` : ""} caught:`, error, errorInfo);
    this.props.onError?.(error, errorInfo);
  }

  reset = () => {
    this.setState({ error: null });
  };

  render() {
    const { error } = this.state;
    if (!error) return this.props.children;

    if (this.props.fallback) {
      return this.props.fallback(error, this.reset);
    }

    return (
      <div className="flex flex-col items-center justify-center gap-3 p-8 rounded-xl border border-red-500/20 bg-red-500/5 text-center">
        <AlertTriangle className="w-8 h-8 text-red-400/70" />
        <div>
          <p className="text-sm font-medium text-white/80">
            {this.props.section ? `${this.props.section} ran into a problem` : "Something went wrong"}
          </p>
          <p className="text-xs text-white/40 mt-1 max-w-sm">
            {error.message || "An unexpected error occurred while rendering this section."}
          </p>
        </div>
        <button
          onClick={this.reset}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/15 text-white/70 hover:text-white text-xs transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Try again
        </button>
      </div>
    );
  }
}
