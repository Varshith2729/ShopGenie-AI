import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { dashboardApi } from '../../services/api';
import { useAuth } from '../../context/AuthContext';
import { 
  BookOpen, 
  HelpCircle, 
  Clock, 
  CheckCircle, 
  ThumbsUp, 
  ThumbsDown, 
  ExternalLink, 
  Copy, 
  Check, 
  AlertTriangle, 
  ArrowRight, 
  Loader2,
  Store,
  Sparkles,
  Activity
} from 'lucide-react';

const DashboardPage = () => {
  const { shop } = useAuth();
  const [data, setData] = useState(null);
  const [recentQuestions, setRecentQuestions] = useState([]);
  const [recentActivities, setRecentActivities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const fetchDashboard = async () => {
      try {
        const [statsRes, recentRes] = await Promise.all([
          dashboardApi.getStats(),
          dashboardApi.getRecentQuestions(),
        ]);
        if (statsRes.data?.success) {
          setData(statsRes.data.data);
        }
        if (recentRes.data?.success) {
          setRecentQuestions(recentRes.data.data.recent_questions || []);
          setRecentActivities(recentRes.data.data.recent_activities || []);
        }
      } catch (err) {
        console.error("Failed to load dashboard data", err);
      } finally {
        setLoading(false);
      }
    };
    fetchDashboard();
  }, []);

  const publicUrl = data?.public_url || `${window.location.origin}/s/${shop?.slug || ''}`;

  const handleCopyLink = () => {
    navigator.clipboard.writeText(publicUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] space-y-3">
        <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
        <p className="text-sm text-slate-500 font-medium">Loading shop metrics...</p>
      </div>
    );
  }

  const stats = data?.stats || {};

  return (
    <div className="space-y-6">
      {/* Top Banner: Public Chatbot Link */}
      <div className="bg-gradient-to-r from-blue-600 to-indigo-700 rounded-2xl p-6 text-white shadow-lg shadow-blue-500/10">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-white/20 text-xs font-semibold backdrop-blur-md mb-2">
              <Sparkles className="w-3.5 h-3.5 text-blue-200" />
              <span>Public Customer Chatbot URL</span>
            </div>
            <h2 className="text-xl sm:text-2xl font-black tracking-tight">{shop?.shop_name}</h2>
            <p className="text-xs sm:text-sm text-blue-100 mt-1 max-w-xl">
              Share this link with customers on Google Maps, WhatsApp, or Instagram bio.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <div className="bg-black/20 border border-white/20 rounded-xl px-3 py-2 text-xs font-mono text-white select-all">
              {publicUrl}
            </div>
            <button
              onClick={handleCopyLink}
              className="inline-flex items-center space-x-1.5 px-4 py-2 rounded-xl bg-white text-slate-900 text-xs font-bold hover:bg-blue-50 transition shadow-sm"
            >
              {copied ? <Check className="w-4 h-4 text-emerald-600" /> : <Copy className="w-4 h-4 text-slate-600" />}
              <span>{copied ? 'Copied Link!' : 'Copy Link'}</span>
            </button>
            <a
              href={`/s/${shop?.slug}`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center space-x-1.5 px-4 py-2 rounded-xl bg-blue-500/40 border border-white/30 text-white text-xs font-bold hover:bg-blue-500/60 transition shadow-sm"
            >
              <ExternalLink className="w-4 h-4" />
              <span>Open Chatbot</span>
            </a>
          </div>
        </div>
      </div>

      {/* Pending Questions Alert */}
      {stats.pending_questions > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-2xl p-4 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-amber-100 text-amber-700 flex items-center justify-center shrink-0">
              <AlertTriangle className="w-5 h-5 text-amber-600" />
            </div>
            <div>
              <h4 className="text-sm font-bold text-amber-900">
                {stats.pending_questions} Pending Customer {stats.pending_questions === 1 ? 'Question' : 'Questions'}
              </h4>
              <p className="text-xs text-amber-700">
                Customers are waiting for your answer. Answering will notify them by email and teach the AI.
              </p>
            </div>
          </div>
          <Link
            to="/admin/questions?status=pending"
            className="inline-flex items-center space-x-1 px-3 py-1.5 rounded-lg bg-amber-600 text-white text-xs font-semibold hover:bg-amber-700 transition shrink-0"
          >
            <span>Review & Answer</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      )}

      {/* 6 Key Metrics Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {/* Card 1: Knowledge Entries */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
          <div className="w-9 h-9 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center mb-3">
            <BookOpen className="w-5 h-5" />
          </div>
          <div className="text-2xl font-black text-slate-900">{stats.total_knowledge || 0}</div>
          <div className="text-xs font-semibold text-slate-500 mt-1">Knowledge Entries</div>
        </div>

        {/* Card 2: Total Questions */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
          <div className="w-9 h-9 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center mb-3">
            <HelpCircle className="w-5 h-5" />
          </div>
          <div className="text-2xl font-black text-slate-900">{stats.total_questions || 0}</div>
          <div className="text-xs font-semibold text-slate-500 mt-1">Total Questions</div>
        </div>

        {/* Card 3: Pending Questions */}
        <div className={`p-5 rounded-2xl border shadow-sm ${
          stats.pending_questions > 0 ? 'bg-amber-50/60 border-amber-200' : 'bg-white border-slate-200'
        }`}>
          <div className={`w-9 h-9 rounded-xl flex items-center justify-center mb-3 ${
            stats.pending_questions > 0 ? 'bg-amber-100 text-amber-600' : 'bg-slate-100 text-slate-600'
          }`}>
            <Clock className="w-5 h-5" />
          </div>
          <div className="text-2xl font-black text-slate-900">{stats.pending_questions || 0}</div>
          <div className="text-xs font-semibold text-slate-500 mt-1">Pending Questions</div>
        </div>

        {/* Card 4: Answered Questions */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
          <div className="w-9 h-9 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center mb-3">
            <CheckCircle className="w-5 h-5" />
          </div>
          <div className="text-2xl font-black text-slate-900">{stats.answered_questions || 0}</div>
          <div className="text-xs font-semibold text-slate-500 mt-1">Answered Questions</div>
        </div>

        {/* Card 5: Good AI Answers */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
          <div className="w-9 h-9 rounded-xl bg-teal-50 text-teal-600 flex items-center justify-center mb-3">
            <ThumbsUp className="w-5 h-5" />
          </div>
          <div className="text-2xl font-black text-slate-900">{stats.good_answers || 0}</div>
          <div className="text-xs font-semibold text-slate-500 mt-1">Good AI Answers</div>
        </div>

        {/* Card 6: Bad AI Answers */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
          <div className="w-9 h-9 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center mb-3">
            <ThumbsDown className="w-5 h-5" />
          </div>
          <div className="text-2xl font-black text-slate-900">{stats.bad_answers || 0}</div>
          <div className="text-xs font-semibold text-slate-500 mt-1">Bad AI Answers</div>
        </div>
      </div>

      {/* Two Column Layout: Recent Questions & Activity Stream */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Customer Questions */}
        <div className="lg:col-span-2 bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
          <div className="flex items-center justify-between mb-5">
            <div>
              <h3 className="text-base font-bold text-slate-900">Recent Customer Inquiries</h3>
              <p className="text-xs text-slate-500">Live stream of questions received via your chatbot</p>
            </div>
            <Link
              to="/admin/questions"
              className="text-xs font-semibold text-blue-600 hover:text-blue-700 flex items-center space-x-1"
            >
              <span>View All</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          {recentQuestions.length === 0 ? (
            <div className="text-center py-10 bg-slate-50 rounded-xl border border-dashed border-slate-200">
              <HelpCircle className="w-8 h-8 text-slate-300 mx-auto mb-2" />
              <p className="text-sm font-semibold text-slate-600">No questions yet</p>
              <p className="text-xs text-slate-400 mt-1">Share your chatbot link to receive inquiries.</p>
            </div>
          ) : (
            <div className="divide-y divide-slate-100">
              {recentQuestions.map((q) => (
                <div key={q.id} className="py-3.5 flex items-start justify-between gap-4">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center space-x-2">
                      <span className="font-semibold text-xs text-slate-900">{q.customer_name}</span>
                      <span className="text-[10px] text-slate-400">&bull; {new Date(q.created_at).toLocaleDateString()}</span>
                    </div>
                    <p className="text-xs text-slate-700 font-medium mt-1 truncate">{q.question}</p>
                    {q.ai_answer && (
                      <p className="text-[11px] text-slate-500 mt-0.5 truncate">
                        <span className="font-semibold text-blue-600">AI:</span> {q.ai_answer}
                      </p>
                    )}
                  </div>
                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider shrink-0 ${
                    q.status === 'answered'
                      ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                      : 'bg-amber-50 text-amber-700 border border-amber-200'
                  }`}>
                    {q.status}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Activity Stream */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
          <div className="flex items-center space-x-2 mb-4">
            <Activity className="w-4 h-4 text-blue-600" />
            <h3 className="text-base font-bold text-slate-900">Recent Shop Activity</h3>
          </div>

          {recentActivities.length === 0 ? (
            <p className="text-xs text-slate-400 py-6 text-center">No recent activity logged.</p>
          ) : (
            <div className="space-y-3.5">
              {recentActivities.map((act) => (
                <div key={act.id} className="text-xs border-l-2 border-blue-500 pl-3 py-0.5">
                  <div className="font-semibold text-slate-800 capitalize">
                    {act.action.replace(/_/g, ' ')}
                  </div>
                  <p className="text-[11px] text-slate-500 truncate">{act.details}</p>
                  <span className="text-[10px] text-slate-400">
                    {new Date(act.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;
