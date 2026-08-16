
import { BrowserRouter, Route, Routes, Navigate } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import { ProtectedRoute } from './components/auth/ProtectedRoute'
import { Login } from './pages/Login'
import { DashboardShell } from './components/layout/DashboardShell'
import { Dashboard } from './pages/Dashboard/Dashboard'

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Public Routes */}
          <Route path="/login" element={<Login />} />

          {/* Protected Routes */}
          <Route element={<ProtectedRoute />}>
            <Route element={<DashboardShell />}>
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="/dashboard" element={<Dashboard />} />
              {/* Placeholders for sidebar routes */}
              <Route path="/operations/*" element={<div className="p-8">Operations Placeholder</div>} />
              <Route path="/analytics/*" element={<div className="p-8">Analytics Placeholder</div>} />
              <Route path="/administration/*" element={<div className="p-8">Administration Placeholder</div>} />
            </Route>
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
