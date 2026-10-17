import { Component, ErrorInfo, ReactNode } from 'react'

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  }

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo)
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null })
    window.location.href = '/'
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center p-6 bg-[#F5F7F5] text-[#192923]">
          <div className="max-w-md w-full bg-white border border-[#DCE4DE] rounded-xl p-8 shadow-sm text-center">
            <div className="w-10 h-10 bg-[#F9ECEB] text-[#A83F3D] rounded-lg flex items-center justify-center mx-auto mb-4 font-semibold text-lg border border-[#F9ECEB]">
              !
            </div>
            <h2 className="text-lg font-semibold mb-2 text-[#192923]">Application Error</h2>
            <p className="text-sm text-[#52635B] mb-6">
              {this.state.error?.message || 'An unexpected rendering error occurred.'}
            </p>
            <button
              onClick={this.handleReset}
              className="px-5 py-2.5 bg-[#176B57] hover:bg-[#105544] text-white rounded-lg text-sm font-medium transition-colors"
            >
              Reload Application
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
