import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './store/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import Navbar from './components/Navbar';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import Verify from './pages/Verify';
import Results from './pages/Results';
import History from './pages/History';
import PublisherRegister from './pages/PublisherRegister';
import AdminPanel from './pages/AdminPanel';
import SystemStatus from './pages/SystemStatus';

function Layout({ children }) {
  return (
    <div className="min-h-screen bg-slate-900">
      <Navbar />
      <main>{children}</main>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public routes */}
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />

          {/* Protected routes */}
          <Route path="/dashboard" element={
            <ProtectedRoute>
              <Layout><Dashboard /></Layout>
            </ProtectedRoute>
          } />
          <Route path="/verify" element={
            <ProtectedRoute>
              <Layout><Verify /></Layout>
            </ProtectedRoute>
          } />
          <Route path="/results/:id" element={
            <ProtectedRoute>
              <Layout><Results /></Layout>
            </ProtectedRoute>
          } />
          <Route path="/history" element={
            <ProtectedRoute>
              <Layout><History /></Layout>
            </ProtectedRoute>
          } />
          <Route path="/publisher" element={
            <ProtectedRoute requiredRole={['PUBLISHER', 'ADMIN']}>
              <Layout><PublisherRegister /></Layout>
            </ProtectedRoute>
          } />
          <Route path="/admin" element={
            <ProtectedRoute requiredRole="ADMIN">
              <Layout><AdminPanel /></Layout>
            </ProtectedRoute>
          } />
          <Route path="/status" element={
            <ProtectedRoute>
              <Layout><SystemStatus /></Layout>
            </ProtectedRoute>
          } />

          {/* Redirect root */}
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
