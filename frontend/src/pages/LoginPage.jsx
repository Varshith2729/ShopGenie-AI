import React, { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Bot, Mail, Lock, AlertCircle, Loader2, Sparkles, Store } from 'lucide-react';

const LoginPage = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(
    searchParams.get('session_expired') ? 'Your session expired. Please sign in again.' : ''
  );
  const [forgotModal, setForgotModal] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const result = await login(email, password);
      if (result.success) {
        navigate('/admin/dashboard');
      } else {
        setError(result.message || 'Invalid email or password.');
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Login failed. Please check credentials.');
    } finally {
      setLoading(false);
    }
  };

  const handleQuickDemo = (demoEmail, demoPassword) => {
    setEmail(demoEmail);
    setPassword(demoPassword);
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <Link to="/" className="inline-flex items-center space-x-2.5">
          <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center text-white shadow-md shadow-blue-500/20">
            <Bot className="w-6 h-6" />
          </div>
          <span className="font-extrabold text-2xl text-slate-900 tracking-tight">Shop FAQ Bot</span>
        </Link>
        <h2 className="mt-6 text-2xl sm:text-3xl font-extrabold text-slate-900">
          Owner Portal Sign In
        </h2>
        <p className="mt-2 text-sm text-slate-600">
          Access your shop admin dashboard, knowledge base, and questions.
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-6 sm:px-10 shadow-sm border border-slate-200 rounded-2xl">
          {error && (
            <div className="mb-6 p-4 rounded-xl bg-red-50 border border-red-200 flex items-start space-x-3 text-red-700 text-sm">
              <AlertCircle className="w-5 h-5 shrink-0 mt-0.5 text-red-500" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Owner Email
              </label>
              <div className="relative">
                <Mail className="w-5 h-5 text-slate-400 absolute left-3 top-3" />
                <input
                  type="email"
                  required
                  placeholder="ravi@gmail.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider">
                  Password
                </label>
                <button
                  type="button"
                  onClick={() => setForgotModal(true)}
                  className="text-xs text-blue-600 hover:text-blue-700 font-medium"
                >
                  Forgot password?
                </button>
              </div>
              <div className="relative">
                <Lock className="w-5 h-5 text-slate-400 absolute left-3 top-3" />
                <input
                  type="password"
                  required
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 px-4 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-sm transition shadow-md shadow-blue-500/25 flex items-center justify-center space-x-2 disabled:opacity-60"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Signing in...</span>
                </>
              ) : (
                <span>Sign In to Admin Dashboard</span>
              )}
            </button>
          </form>

          {/* Quick Demo Login Helpers */}
          <div className="mt-8 pt-6 border-t border-slate-100">
            <div className="flex items-center space-x-1 text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">
              <Sparkles className="w-3.5 h-3.5 text-amber-500" />
              <span>One-Click Demo Accounts</span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => handleQuickDemo('ravi@gmail.com', 'password123')}
                className="p-2.5 rounded-xl border border-slate-200 text-left hover:bg-blue-50 hover:border-blue-200 transition group"
              >
                <div className="flex items-center space-x-1.5 text-xs font-bold text-slate-800 group-hover:text-blue-700">
                  <Store className="w-3.5 h-3.5 text-blue-600" />
                  <span>Ravi Mobiles</span>
                </div>
                <div className="text-[10px] text-slate-400 font-mono">ravi@gmail.com</div>
              </button>
              <button
                type="button"
                onClick={() => handleQuickDemo('sri@gmail.com', 'password123')}
                className="p-2.5 rounded-xl border border-slate-200 text-left hover:bg-indigo-50 hover:border-indigo-200 transition group"
              >
                <div className="flex items-center space-x-1.5 text-xs font-bold text-slate-800 group-hover:text-indigo-700">
                  <Store className="w-3.5 h-3.5 text-indigo-600" />
                  <span>Sri Fashion</span>
                </div>
                <div className="text-[10px] text-slate-400 font-mono">sri@gmail.com</div>
              </button>
            </div>
          </div>

          <div className="mt-6 text-center text-sm text-slate-600">
            Don't have a shop account?{' '}
            <Link to="/register" className="font-semibold text-blue-600 hover:text-blue-700">
              Register here
            </Link>
          </div>
        </div>
      </div>

      {/* Forgot Password Modal */}
      {forgotModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-sm w-full p-6 shadow-xl border border-slate-200 text-center">
            <div className="w-12 h-12 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center mx-auto mb-4">
              <Lock className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-bold text-slate-900">Reset Password</h3>
            <p className="mt-2 text-xs text-slate-600 leading-relaxed">
              In this environment, you can use the pre-configured password <code className="bg-slate-100 px-1 py-0.5 rounded text-blue-600 font-bold font-mono">password123</code> or register a new shop with your own password.
            </p>
            <button
              onClick={() => setForgotModal(false)}
              className="mt-5 w-full py-2.5 px-4 rounded-xl bg-slate-900 text-white font-semibold text-xs hover:bg-slate-800 transition"
            >
              Got it
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default LoginPage;

