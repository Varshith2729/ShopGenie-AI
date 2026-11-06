import React from 'react';
import { Link } from 'react-router-dom';
import { 
  Bot, 
  Sparkles, 
  Share2, 
  ShieldCheck, 
  Mail, 
  TrendingUp, 
  ArrowRight, 
  CheckCircle2, 
  Store, 
  Clock, 
  MessageSquare,
  Zap
} from 'lucide-react';

const LandingPage = () => {
  return (
    <div className="min-h-screen bg-slate-50 flex flex-col selection:bg-blue-500 selection:text-white">
      {/* Navigation */}
      <nav className="h-20 bg-white/80 backdrop-blur-md border-b border-slate-200/80 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-full flex items-center justify-between">
          <Link to="/" className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center text-white shadow-md shadow-blue-500/20">
              <Bot className="w-6 h-6" />
            </div>
            <div>
              <span className="font-extrabold text-slate-900 text-lg tracking-tight">Shop FAQ Bot</span>
              <span className="hidden sm:inline-block ml-2 px-2 py-0.5 text-[10px] font-bold bg-blue-50 text-blue-700 rounded-full border border-blue-200">
                SaaS v1.0
              </span>
            </div>
          </Link>

          <div className="flex items-center space-x-3 sm:space-x-4">
            <Link 
              to="/login"
              className="text-sm font-semibold text-slate-700 hover:text-blue-600 px-3 py-2 rounded-lg transition"
            >
              Sign In
            </Link>
            <Link
              to="/register"
              className="inline-flex items-center space-x-1.5 px-4 py-2.5 rounded-xl bg-blue-600 text-sm font-semibold text-white hover:bg-blue-700 transition shadow-md shadow-blue-500/20"
            >
              <span>Get Started Free</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative overflow-hidden pt-12 pb-20 lg:pt-20 lg:pb-28 bg-gradient-to-b from-blue-50/50 via-white to-slate-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10 text-center">
          <div className="inline-flex items-center space-x-2 px-3 py-1.5 rounded-full bg-blue-100/70 border border-blue-200 text-blue-800 text-xs font-semibold mb-6 animate-pulse">
            <Sparkles className="w-3.5 h-3.5 text-blue-600" />
            <span>Multi-Tenant AI-Powered Customer Support</span>
          </div>

          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold text-slate-900 tracking-tight max-w-4xl mx-auto leading-tight">
            Your Shop. Your AI Assistant. <br className="hidden sm:inline" />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-indigo-600">
              Your Customers, Always Connected.
            </span>
          </h1>

          <p className="mt-6 text-lg sm:text-xl text-slate-600 max-w-2xl mx-auto leading-relaxed">
            Teach your AI about your shop and let it answer customer questions 24/7. 
            Strict tenant isolation, automated email escalation, and continuous self-improving answers.
          </p>

          <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              to="/register"
              className="w-full sm:w-auto px-8 py-3.5 rounded-xl bg-blue-600 text-base font-bold text-white hover:bg-blue-700 transition shadow-lg shadow-blue-500/25 flex items-center justify-center space-x-2"
            >
              <span>Create Your Shop Free</span>
              <ArrowRight className="w-5 h-5" />
            </Link>
            <Link
              to="/login"
              className="w-full sm:w-auto px-8 py-3.5 rounded-xl bg-white text-base font-semibold text-slate-700 hover:bg-slate-50 border border-slate-200 transition shadow-sm flex items-center justify-center space-x-2"
            >
              <span>Shop Owner Login</span>
            </Link>
          </div>

          {/* Demo Shops Showcase Pills */}
          <div className="mt-12 p-4 rounded-2xl bg-white border border-slate-200 max-w-2xl mx-auto shadow-sm">
            <p className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">
              Explore Live Demo Shops (Pre-seeded with Strict Isolation)
            </p>
            <div className="flex flex-wrap items-center justify-center gap-3">
              <a
                href="/s/ravi-mobiles"
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center space-x-2 px-4 py-2 rounded-xl bg-blue-50 border border-blue-200 text-blue-700 text-xs font-semibold hover:bg-blue-100 transition"
              >
                <Store className="w-3.5 h-3.5" />
                <span>Ravi Mobiles (/s/ravi-mobiles)</span>
              </a>
              <a
                href="/s/sri-fashion"
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center space-x-2 px-4 py-2 rounded-xl bg-indigo-50 border border-indigo-200 text-indigo-700 text-xs font-semibold hover:bg-indigo-100 transition"
              >
                <Store className="w-3.5 h-3.5" />
                <span>Sri Fashion (/s/sri-fashion)</span>
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* Feature Highlights Grid */}
      <section className="py-20 bg-white border-y border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <h2 className="text-3xl font-extrabold text-slate-900 tracking-tight">
              Engineered For Modern Local & Online Businesses
            </h2>
            <p className="mt-3 text-slate-600 text-base">
              Say goodbye to repetitive WhatsApp inquiries and missed phone calls during rush hours.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {/* Card 1 */}
            <div className="p-6 rounded-2xl bg-slate-50 border border-slate-200/80 hover:shadow-md transition">
              <div className="w-12 h-12 rounded-xl bg-blue-100 text-blue-600 flex items-center justify-center mb-5">
                <Store className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-bold text-slate-900 mb-2">Free Shop Registration</h3>
              <p className="text-sm text-slate-600 leading-relaxed">
                Create your tenant account in seconds. Get an immediate unique URL slug for your storefront chatbot.
              </p>
            </div>

            {/* Card 2 */}
            <div className="p-6 rounded-2xl bg-slate-50 border border-slate-200/80 hover:shadow-md transition">
              <div className="w-12 h-12 rounded-xl bg-indigo-100 text-indigo-600 flex items-center justify-center mb-5">
                <ShieldCheck className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-bold text-slate-900 mb-2">Strict Tenant Isolation</h3>
              <p className="text-sm text-slate-600 leading-relaxed">
                AI answers strictly using your shop's knowledge base. Zero cross-shop leakage and no hallucinated pricing.
              </p>
            </div>

            {/* Card 3 */}
            <div className="p-6 rounded-2xl bg-slate-50 border border-slate-200/80 hover:shadow-md transition">
              <div className="w-12 h-12 rounded-xl bg-emerald-100 text-emerald-600 flex items-center justify-center mb-5">
                <Share2 className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-bold text-slate-900 mb-2">Personalized Chatbot Link</h3>
              <p className="text-sm text-slate-600 leading-relaxed">
                Add your link to your Google Maps listing, Instagram bio, or print it as a QR code at your checkout counter.
              </p>
            </div>

            {/* Card 4 */}
            <div className="p-6 rounded-2xl bg-slate-50 border border-slate-200/80 hover:shadow-md transition">
              <div className="w-12 h-12 rounded-xl bg-amber-100 text-amber-600 flex items-center justify-center mb-5">
                <Mail className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-bold text-slate-900 mb-2">Email Escalation Pipeline</h3>
              <p className="text-sm text-slate-600 leading-relaxed">
                If the AI doesn't know the answer, it creates a pending ticket. Once you answer, the customer gets an instant email!
              </p>
            </div>

            {/* Card 5 */}
            <div className="p-6 rounded-2xl bg-slate-50 border border-slate-200/80 hover:shadow-md transition">
              <div className="w-12 h-12 rounded-xl bg-purple-100 text-purple-600 flex items-center justify-center mb-5">
                <TrendingUp className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-bold text-slate-900 mb-2">Continuous Learning Loop</h3>
              <p className="text-sm text-slate-600 leading-relaxed">
                Rate AI answers as Good or Bad. Corrections automatically feed back into your knowledge base for future inquiries.
              </p>
            </div>

            {/* Card 6 */}
            <div className="p-6 rounded-2xl bg-slate-50 border border-slate-200/80 hover:shadow-md transition">
              <div className="w-12 h-12 rounded-xl bg-cyan-100 text-cyan-600 flex items-center justify-center mb-5">
                <Clock className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-bold text-slate-900 mb-2">36-Hour Customer Memory</h3>
              <p className="text-sm text-slate-600 leading-relaxed">
                Customers enter their name and email once. The session persists for 36 hours without repetitive sign-ins.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section className="py-20 bg-slate-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <h2 className="text-3xl font-extrabold text-slate-900 tracking-tight">
              How It Works in 4 Simple Steps
            </h2>
            <p className="mt-3 text-slate-600 text-base">
              Set up your AI customer support in less than 2 minutes.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div className="bg-white p-6 rounded-2xl border border-slate-200 relative">
              <div className="w-8 h-8 rounded-full bg-blue-600 text-white font-bold text-sm flex items-center justify-center mb-4">1</div>
              <h4 className="font-bold text-slate-900 mb-1">Create Shop</h4>
              <p className="text-xs text-slate-600">Register your shop name and pick a custom URL slug.</p>
            </div>
            <div className="bg-white p-6 rounded-2xl border border-slate-200 relative">
              <div className="w-8 h-8 rounded-full bg-blue-600 text-white font-bold text-sm flex items-center justify-center mb-4">2</div>
              <h4 className="font-bold text-slate-900 mb-1">Add Knowledge</h4>
              <p className="text-xs text-slate-600">Enter your shop timings, product brands, returns, and FAQs.</p>
            </div>
            <div className="bg-white p-6 rounded-2xl border border-slate-200 relative">
              <div className="w-8 h-8 rounded-full bg-blue-600 text-white font-bold text-sm flex items-center justify-center mb-4">3</div>
              <h4 className="font-bold text-slate-900 mb-1">Share Public Link</h4>
              <p className="text-xs text-slate-600">Customers open your custom link and chat without registering.</p>
            </div>
            <div className="bg-white p-6 rounded-2xl border border-slate-200 relative">
              <div className="w-8 h-8 rounded-full bg-blue-600 text-white font-bold text-sm flex items-center justify-center mb-4">4</div>
              <h4 className="font-bold text-slate-900 mb-1">Auto-Improve</h4>
              <p className="text-xs text-slate-600">Answer pending questions and rate answers to make your AI smarter.</p>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="mt-auto bg-slate-900 text-slate-400 py-12 border-t border-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white">
              <Bot className="w-5 h-5" />
            </div>
            <span className="font-bold text-white text-base">Shop FAQ Bot</span>
          </div>
          <p className="text-xs text-slate-500">
            &copy; {new Date().getFullYear()} Shop FAQ Bot. Multi-Tenant AI Platform. All rights reserved.
          </p>
          <div className="flex items-center space-x-6 text-xs">
            <Link to="/login" className="hover:text-white transition">Sign In</Link>
            <Link to="/register" className="hover:text-white transition">Register Shop</Link>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;

