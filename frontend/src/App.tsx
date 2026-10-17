import { BrowserRouter, Route, Routes, Navigate } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import { ProtectedRoute } from './components/auth/ProtectedRoute'
import { Login } from './pages/Login'
import { DashboardShell } from './components/layout/DashboardShell'
import { Dashboard } from './pages/Dashboard/Dashboard'
import { CapacityForecasts } from './pages/Forecasts/CapacityForecasts'
import { ModelEvaluation } from './pages/Evaluation/ModelEvaluation'
import { DatasetCatalog } from './pages/Datasets/DatasetCatalog'
import { BedsPage } from './pages/Operations/BedsPage'
import { ResourcesPage } from './pages/Operations/ResourcesPage'
import { PatientsPage } from './pages/Operations/PatientsPage'
import { UsersPage } from './pages/Administration/UsersPage'
import { ErrorBoundary } from './components/common/ErrorBoundary'

function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            {/* Public Routes */}
            <Route path="/login" element={<Login />} />

            {/* Protected Workspace & Operations Routes */}
            <Route element={<ProtectedRoute />}>
              <Route element={<DashboardShell />}>
                <Route path="/" element={<Navigate to="/dashboard" replace />} />
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/forecasts" element={<CapacityForecasts />} />
                <Route path="/evaluation" element={<ModelEvaluation />} />
                <Route path="/datasets" element={<DatasetCatalog />} />
                
                {/* Operations Routes */}
                <Route path="/operations/beds" element={<BedsPage />} />
                <Route path="/operations/resources" element={<ResourcesPage />} />
                <Route path="/operations/patients" element={<PatientsPage />} />
                <Route path="/operations/admissions" element={<PatientsPage />} />
                
                {/* Legacy/Redirect Routes */}
                <Route path="/analytics/historical" element={<Navigate to="/datasets" replace />} />
                <Route path="/analytics/*" element={<Navigate to="/evaluation" replace />} />
                <Route path="/operations" element={<Navigate to="/operations/beds" replace />} />

                {/* Administration Routes */}
                <Route path="/administration/users" element={<UsersPage />} />
                <Route path="/administration/*" element={<Navigate to="/administration/users" replace />} />

                {/* Catch-all */}
                <Route path="*" element={<Navigate to="/dashboard" replace />} />
              </Route>
            </Route>
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </ErrorBoundary>
  )
}

export default App
