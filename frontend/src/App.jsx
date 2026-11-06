import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';

// Layouts
import AdminLayout from './layouts/AdminLayout';

// Public Pages
import LandingPage from './pages/LandingPage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import PublicChatPage from './pages/PublicChatPage';
import NotFoundPage from './pages/NotFoundPage';

// Admin Pages
import DashboardPage from './pages/admin/DashboardPage';
import KnowledgeBasePage from './pages/admin/KnowledgeBasePage';
import QuestionsPage from './pages/admin/QuestionsPage';
import RateAnswersPage from './pages/admin/RateAnswersPage';
import ShopSettingsPage from './pages/admin/ShopSettingsPage';

// Protected Route Guard
const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return children;
};

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public Routes */}
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          
          {/* Customer Chatbot Public Route */}
          <Route path="/s/:slug" element={<PublicChatPage />} />

          {/* Protected Shop Owner Admin Portal */}
          <Route
            path="/admin"
            element={
              <ProtectedRoute>
                <AdminLayout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Navigate to="/admin/dashboard" replace />} />
            <Route path="dashboard" element={<DashboardPage />} />
            <Route path="knowledge" element={<KnowledgeBasePage />} />
            <Route path="questions" element={<QuestionsPage />} />
            <Route path="rate-answers" element={<RateAnswersPage />} />
            <Route path="settings" element={<ShopSettingsPage />} />
          </Route>

          {/* 404 Catch-All */}
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;

