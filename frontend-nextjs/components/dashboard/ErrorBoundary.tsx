// components/dashboard/ErrorBoundary.tsx
'use client';

import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle } from 'lucide-react';

interface Props {
 children: ReactNode;
 error?: any;
}

interface State {
 hasError: boolean;
 error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
 public state: State = {
 hasError: false
 };

 public static getDerivedStateFromError(error: Error): State {
 return { hasError: true, error };
 }

 public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
 console.error('Uncaught error:', error, errorInfo);
 }

 public render() {
 // If there's a prop error, show it
 if (this.props.error) {
 return (
 <div className="error-container m-4">
 <div className="flex items-center gap-2 mb-2">
 <AlertTriangle className="h-5 w-5 text-red-500" />
 <h3 className="font-semibold">Application Error</h3>
 </div>
 <p className="text-sm">{this.props.error}</p>
 </div>
 );
 }

 // If there's a caught error, show it
 if (this.state.hasError) {
 return (
 <div className="error-container m-4">
 <div className="flex items-center gap-2 mb-2">
 <AlertTriangle className="h-5 w-5 text-red-500" />
 <h3 className="font-semibold">Something went wrong</h3>
 </div>
 <p className="text-sm mb-4">
 {this.state.error?.message || 'An unexpected error occurred'}
 </p>
 <button
 onClick={() => this.setState({ hasError: false, error: undefined })}
 className="px-3 py-1 bg-red-100 text-red-800 text-sm rounded hover:bg-red-200 transition-colors"
 >
 Try again
 </button>
 </div>
 );
 }

 return this.props.children;
 }
}