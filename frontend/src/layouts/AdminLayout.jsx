import React, { useState } from 'react';
import { NavLink, Outlet, useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { 
  LayoutDashboard, 
  BookOpen, 
  HelpCircle, 
  ThumbsUp, 
  Settings, 
  LogOut, 
  ExternalLink, 
  Copy, 
  Check, 
  Store, 
  Menu, 
  X,
  Bot
} from 'lucide-react';

const AdminLayout = () => {
  const { user, shop, logout } = useAuth();
  const navigate = useNavigate();
  const [copied, setCopied] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const publicUrl = `${window.location.origin}/s/${shop?.slug || ''}`;

  const handleCopyLink = () => {
    if (publicUrl) {
      navigator.clipboard.writeText(publicUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const navItems = [
    { name: 'Dashboard', path: '/admin/dashboard', icon: LayoutDashboard },
    { name: 'Knowledge Base', path: '/admin/knowledge', icon: BookOpen },
    { name: 'Customer Questions', path: '/admin/questions', icon: HelpCircle },
    { name: 'Rate Answers', path: '/admin/rate-answers', icon: ThumbsUp },
    { name: 'Shop Settings', path: '/admin/settings', icon: Settings },
  ];

  return (
    <div className="min-h-screen bg-slate-50 flex">
      {/* Sidebar for Desktop */}
      <aside className="hidden md:flex flex-col w-64 bg-white border-r border-slate-200 fixed inset-y-0 z-30">
        {/* Brand Header */}
        <div className="h-16 px-6 border-b border-slate-100 flex items-center justify-between">
          <Link to="/admin/dashboard" className="flex items-center space-x-2.5">
            <div className="w-9 h-9 rounded-xl bg-blue-600 flex items-center justify-center text-white shadow-md shadow-blue-500/20">
              <Bot className="w-5 h-5" />
            </div>
            <div>
              <span className="font-bold text-slate-900 text-base tracking-tight">Shop FAQ Bot</span>
              <span className="block text-[10px] uppercase tracking-wider text-blue-600 font-semibold">Tenant Admin</span>
            </div>
          </Link>
        </div>

        {/* Current Shop Badge */}
        <div className="p-4 mx-3 my-2 rounded-xl bg-slate-50 border border-slate-150">
          <div className="flex items-center space-x-2 text-xs text-slate-500 font-medium mb-1">
            <Store className="w-3.5 h-3.5 text-blue-600" />
            <span>ACTIVE SHOP</span>
          </div>
          <div className="font-bold text-slate-900 text-sm truncate">{shop?.shop_name || 'My Shop'}</div>
          <div className="text-xs text-slate-400 font-mono truncate">/s/{shop?.slug}</div>
        </div>

        {/* Navigation Links */}
        <nav className="flex-1 px-3 py-2 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  `flex items-center px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-blue-50 text-blue-700 font-semibold'
                      : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                  }`
                }
              >
                <Icon className="w-4.5 h-4.5 mr-3 shrink-0" />
                {item.name}
              </NavLink>
            );
          })}
        </nav>

        {/* User Info & Logout */}
        <div className="p-4 border-t border-slate-100">
          <div className="flex items-center justify-between mb-3">
            <div className="truncate">
              <p className="text-sm font-medium text-slate-900 truncate">{user?.full_name}</p>
              <p className="text-xs text-slate-400 truncate">{user?.email}</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="w-full flex items-center justify-center space-x-2 px-3 py-2 rounded-lg text-sm font-medium text-red-600 hover:bg-red-50 transition"
          >
            <LogOut className="w-4 h-4" />
            <span>Sign Out</span>
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col md:pl-64 min-w-0">
        {/* Top Navbar */}
        <header className="h-16 bg-white border-b border-slate-200 sticky top-0 z-20 px-4 md:px-8 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="md:hidden p-2 text-slate-500 hover:bg-slate-100 rounded-lg"
            >
              {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
            <div className="flex items-center space-x-2">
              <span className="text-sm font-medium text-slate-500 hidden sm:inline">Shop:</span>
              <span className="font-semibold text-slate-800 text-sm md:text-base">{shop?.shop_name}</span>
            </div>
          </div>

          {/* Quick Chatbot Link Actions */}
          <div className="flex items-center space-x-2 sm:space-x-3">
            <div className="hidden lg:flex items-center text-xs text-slate-500 bg-slate-100 px-3 py-1.5 rounded-lg font-mono">
              {publicUrl}
            </div>
            <button
              onClick={handleCopyLink}
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border border-slate-200 text-xs font-medium text-slate-700 bg-white hover:bg-slate-50 transition shadow-sm"
              title="Copy public chatbot URL"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5 text-slate-500" />}
              <span>{copied ? 'Copied!' : 'Copy Link'}</span>
            </button>
            <a
              href={`/s/${shop?.slug}`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-blue-600 text-xs font-semibold text-white hover:bg-blue-700 transition shadow-sm shadow-blue-500/20"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              <span>Open Chatbot</span>
            </a>
          </div>
        </header>

        {/* Mobile Navigation Drawer */}
        {mobileMenuOpen && (
          <div className="md:hidden bg-white border-b border-slate-200 px-4 py-3 space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  onClick={() => setMobileMenuOpen(false)}
                  className={({ isActive }) =>
                    `flex items-center px-3 py-2.5 rounded-lg text-sm font-medium ${
                      isActive ? 'bg-blue-50 text-blue-700 font-semibold' : 'text-slate-600'
                    }`
                  }
                >
                  <Icon className="w-4.5 h-4.5 mr-3 shrink-0" />
                  {item.name}
                </NavLink>
              );
            })}
            <button
              onClick={handleLogout}
              className="w-full flex items-center px-3 py-2.5 rounded-lg text-sm font-medium text-red-600 hover:bg-red-50"
            >
              <LogOut className="w-4.5 h-4.5 mr-3" />
              Sign Out
            </button>
          </div>
        )}

        {/* Outlet for Dashboard views */}
        <main className="flex-1 p-4 md:p-8 max-w-7xl w-full mx-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export default AdminLayout;
