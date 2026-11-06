import React from 'react';
import { Link } from 'react-router-dom';
import { Bot, Home } from 'lucide-react';

const NotFoundPage = () => {
  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
      <div className="bg-white p-8 rounded-2xl border border-slate-200 max-w-md w-full text-center shadow-sm">
        <div className="w-16 h-16 rounded-2xl bg-blue-100 text-blue-600 flex items-center justify-center mx-auto mb-4">
          <Bot className="w-8 h-8" />
        </div>
        <h1 className="text-4xl font-extrabold text-slate-900 tracking-tight">404</h1>
        <h2 className="text-lg font-bold text-slate-800 mt-2">Page Not Found</h2>
        <p className="mt-2 text-xs text-slate-500 leading-relaxed">
          The requested page or shop link could not be located.
        </p>
        <Link
          to="/"
          className="mt-6 inline-flex items-center justify-center space-x-2 w-full py-2.5 px-4 rounded-xl bg-blue-600 text-white font-semibold text-xs hover:bg-blue-700 transition shadow-sm"
        >
          <Home className="w-4 h-4" />
          <span>Return to Homepage</span>
        </Link>
      </div>
    </div>
  );
};

export default NotFoundPage;

