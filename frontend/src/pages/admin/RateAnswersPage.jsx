import React, { useState, useEffect } from 'react';
import { feedbackApi } from '../../services/api';
import { 
  ThumbsUp, 
  ThumbsDown, 
  CheckCircle, 
  AlertCircle, 
  Loader2, 
  X, 
  Sparkles, 
  Bot, 
  HelpCircle,
  Check,
  Search,
  Filter,
  Percent,
  MessageSquare
} from 'lucide-react';

const RateAnswersPage = () => {
  const [items, setItems] = useState([]);
  const [stats, setStats] = useState({ total_good: 0, total_bad: 0, good_percentage: 0 });
  const [loading, setLoading] = useState(true);
  const [notification, setNotification] = useState('');

  // Filter & Search state
  const [typeFilter, setTypeFilter] = useState('');
  const [searchQuery, setSearchQuery] = useState('');

  // Bad feedback modal state
  const [badModalItem, setBadModalItem] = useState(null);
  const [reason, setReason] = useState('');
  const [correctAnswer, setCorrectAnswer] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const fetchItems = async () => {
    setLoading(true);
    try {
      const res = await feedbackApi.list({
        type: typeFilter || undefined,
        q: searchQuery.trim() || undefined
      });
      if (res.data?.success) {
        setItems(res.data.data.items || []);
        setStats({
          total_good: res.data.data.total_good || 0,
          total_bad: res.data.data.total_bad || 0,
          good_percentage: res.data.data.good_percentage || 0
        });
      }
    } catch (err) {
      console.error("Failed to load feedback items", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchItems();
  }, [typeFilter, searchQuery]);

  const handleGoodClick = async (questionId) => {
    try {
      const res = await feedbackApi.submitGood(questionId);
      if (res.data?.success) {
        setNotification('Answer marked as Good! Feedback recorded.');
        fetchItems();
      }
    } catch (err) {
      alert(err.response?.data?.message || 'Failed to submit good feedback');
    } finally {
      setTimeout(() => setNotification(''), 3000);
    }
  };

  const openBadModal = (item) => {
    setBadModalItem(item);
    setReason(item.feedback_comment || '');
    setCorrectAnswer(item.correct_answer || '');
    setError('');
  };

  const handleSaveCorrection = async (e) => {
    e.preventDefault();
    if (!reason.trim()) {
      setError('Please explain why this answer is bad or what was incorrect.');
      return;
    }
    if (!correctAnswer.trim()) {
      setError('Please provide the correct answer.');
      return;
    }

    setSubmitting(true);
    setError('');

    try {
      const res = await feedbackApi.submitBad(
        badModalItem.question_id || badModalItem.id,
        reason.trim(),
        correctAnswer.trim()
      );
      if (res.data?.success) {
        setNotification('Correction saved and added to Knowledge Base! Future answers will use this verified information.');
        setBadModalItem(null);
        fetchItems();
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to submit correction');
    } finally {
      setSubmitting(false);
      setTimeout(() => setNotification(''), 4000);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-black text-slate-900 tracking-tight">Rate AI Answers</h1>
        <p className="text-xs sm:text-sm text-slate-500 mt-1">
          Review customer ratings and AI-generated answers. Add verified corrections to immediately reinforce your shop's knowledge base.
        </p>
      </div>

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm flex items-center space-x-4">
          <div className="w-12 h-12 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center font-bold">
            <ThumbsUp className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs font-bold text-slate-400 uppercase tracking-wider">Good AI Answers</div>
            <div className="text-2xl font-black text-slate-900 mt-0.5">{stats.total_good}</div>
          </div>
        </div>

        <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm flex items-center space-x-4">
          <div className="w-12 h-12 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center font-bold">
            <ThumbsDown className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs font-bold text-slate-400 uppercase tracking-wider">Bad AI Answers</div>
            <div className="text-2xl font-black text-slate-900 mt-0.5">{stats.total_bad}</div>
          </div>
        </div>

        <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm flex items-center space-x-4">
          <div className="w-12 h-12 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center font-bold">
            <Percent className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs font-bold text-slate-400 uppercase tracking-wider">Good Answer Rate</div>
            <div className="text-2xl font-black text-blue-600 mt-0.5">{stats.good_percentage}%</div>
          </div>
        </div>
      </div>

      {/* Search & Filters */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white p-3 rounded-2xl border border-slate-200 shadow-sm">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search by customer question..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 rounded-xl border border-slate-200 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        <div className="flex items-center space-x-1.5 self-start sm:self-auto">
          <button
            onClick={() => setTypeFilter('')}
            className={`px-3 py-1.5 rounded-xl text-xs font-bold transition ${
              !typeFilter ? 'bg-blue-600 text-white shadow-xs' : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            All Ratings
          </button>
          <button
            onClick={() => setTypeFilter('good')}
            className={`px-3 py-1.5 rounded-xl text-xs font-bold transition flex items-center space-x-1 ${
              typeFilter === 'good' ? 'bg-emerald-600 text-white shadow-xs' : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            <ThumbsUp className="w-3.5 h-3.5" />
            <span>Good</span>
          </button>
          <button
            onClick={() => setTypeFilter('bad')}
            className={`px-3 py-1.5 rounded-xl text-xs font-bold transition flex items-center space-x-1 ${
              typeFilter === 'bad' ? 'bg-rose-600 text-white shadow-xs' : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            <ThumbsDown className="w-3.5 h-3.5" />
            <span>Bad</span>
          </button>
        </div>
      </div>

      {/* Notification Banner */}
      {notification && (
        <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-semibold flex items-center space-x-2">
          <CheckCircle className="w-4 h-4 text-emerald-600" />
          <span>{notification}</span>
        </div>
      )}

      {/* Structured Rate Answers Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        {loading ? (
          <div className="flex flex-col items-center justify-center py-16 space-y-2">
            <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
            <p className="text-xs text-slate-500">Loading feedback entries...</p>
          </div>
        ) : items.length === 0 ? (
          <div className="text-center py-16 px-4">
            <Bot className="w-10 h-10 text-slate-300 mx-auto mb-2" />
            <h3 className="text-sm font-bold text-slate-800">No Answers Found</h3>
            <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1">
              {typeFilter || searchQuery 
                ? 'No AI responses match the current search or rating filter.' 
                : 'Customer ratings and AI answers will show up here as customers interact with your chatbot.'}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 font-bold uppercase tracking-wider text-[10px]">
                  <th className="px-5 py-3.5">Customer</th>
                  <th className="px-5 py-3.5">Question</th>
                  <th className="px-5 py-3.5">AI Answer</th>
                  <th className="px-5 py-3.5">Rating</th>
                  <th className="px-5 py-3.5">Feedback / Comment</th>
                  <th className="px-5 py-3.5">Date</th>
                  <th className="px-5 py-3.5 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {items.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-50/70 transition">
                    <td className="px-5 py-4 whitespace-nowrap">
                      <div className="font-bold text-slate-900">{item.customer_name}</div>
                      <div className="text-[11px] text-slate-400 font-mono">{item.customer_email}</div>
                    </td>
                    <td className="px-5 py-4 max-w-xs md:max-w-sm">
                      <p className="font-bold text-slate-900 leading-snug">{item.question}</p>
                    </td>
                    <td className="px-5 py-4 max-w-xs md:max-w-md">
                      <p className="text-slate-700 leading-relaxed bg-slate-50 p-2.5 rounded-xl border border-slate-100 text-[11px]">
                        {item.ai_answer}
                      </p>
                      {item.correct_answer && (
                        <div className="mt-1.5 p-2 bg-purple-50 rounded-lg border border-purple-100 text-[11px] text-purple-900">
                          <span className="font-bold flex items-center space-x-1 text-purple-700">
                            <Sparkles className="w-3 h-3" />
                            <span>Saved Knowledge Correction:</span>
                          </span>
                          <p className="mt-0.5">{item.correct_answer}</p>
                        </div>
                      )}
                    </td>
                    <td className="px-5 py-4 whitespace-nowrap">
                      {item.rating === 'good' ? (
                        <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 text-[10px] font-bold">
                          <ThumbsUp className="w-3 h-3" />
                          <span>Good</span>
                        </span>
                      ) : item.rating === 'bad' ? (
                        <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full bg-rose-50 text-rose-700 border border-rose-200 text-[10px] font-bold">
                          <ThumbsDown className="w-3 h-3" />
                          <span>Bad</span>
                        </span>
                      ) : (
                        <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full bg-slate-100 text-slate-500 text-[10px] font-medium">
                          <span>Unrated</span>
                        </span>
                      )}
                    </td>
                    <td className="px-5 py-4 max-w-xs">
                      {item.feedback_comment ? (
                        <span className="text-slate-600 text-[11px] italic">"{item.feedback_comment}"</span>
                      ) : (
                        <span className="text-slate-400 text-[10px]">&mdash;</span>
                      )}
                    </td>
                    <td className="px-5 py-4 whitespace-nowrap text-slate-500 text-[11px]">
                      {item.created_at ? new Date(item.created_at).toLocaleDateString() : 'N/A'}
                    </td>
                    <td className="px-5 py-4 whitespace-nowrap text-right">
                      {item.rating === 'bad' ? (
                        <button
                          onClick={() => openBadModal(item)}
                          className="inline-flex items-center space-x-1 px-3 py-1.5 rounded-lg bg-purple-600 hover:bg-purple-700 text-white font-bold text-xs transition shadow-xs"
                        >
                          <Sparkles className="w-3.5 h-3.5" />
                          <span>{item.correct_answer ? 'Edit Correction' : 'Correct Answer'}</span>
                        </button>
                      ) : (
                        <div className="flex items-center justify-end space-x-1.5">
                          <button
                            onClick={() => handleGoodClick(item.question_id || item.id)}
                            className="p-1.5 rounded-lg border border-slate-200 hover:bg-emerald-50 hover:text-emerald-600 text-slate-500 transition"
                            title="Rate Good"
                          >
                            <ThumbsUp className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => openBadModal(item)}
                            className="p-1.5 rounded-lg border border-slate-200 hover:bg-rose-50 hover:text-rose-600 text-slate-500 transition"
                            title="Mark Bad & Correct"
                          >
                            <ThumbsDown className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Bad Feedback / Knowledge Correction Modal */}
      {badModalItem && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center space-x-2">
                <div className="w-8 h-8 rounded-xl bg-purple-100 text-purple-600 flex items-center justify-center">
                  <Sparkles className="w-4 h-4" />
                </div>
                <h3 className="text-base font-bold text-slate-900">Correct AI Answer</h3>
              </div>
              <button
                onClick={() => setBadModalItem(null)}
                className="p-1 text-slate-400 hover:text-slate-600 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200 mb-4 text-xs space-y-1.5">
              <p className="font-semibold text-slate-800">
                <span className="text-slate-500 font-bold uppercase text-[10px]">Customer:</span> {badModalItem.customer_name} ({badModalItem.customer_email})
              </p>
              <p className="font-semibold text-slate-800">
                <span className="text-slate-500 font-bold uppercase text-[10px]">Question:</span> "{badModalItem.question}"
              </p>
              <p className="text-slate-600 text-[11px]">
                <span className="text-slate-500 font-bold uppercase text-[10px]">AI Answer:</span> {badModalItem.ai_answer}
              </p>
              {badModalItem.feedback_comment && (
                <p className="text-amber-800 bg-amber-50 p-2 rounded border border-amber-200 text-[11px]">
                  <span className="font-bold">Customer Feedback:</span> "{badModalItem.feedback_comment}"
                </p>
              )}
            </div>

            {error && (
              <div className="mb-4 p-3 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs flex items-center space-x-2">
                <AlertCircle className="w-4 h-4 shrink-0 text-red-500" />
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleSaveCorrection} className="space-y-4">
              <div>
                <label className="block text-[11px] font-bold text-slate-700 uppercase tracking-wider mb-1">
                  1. Why was it bad / Correction Reason?
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Incomplete policy details, wrong timing, ambiguous wording..."
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl border border-slate-300 text-xs focus:ring-2 focus:ring-blue-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-[11px] font-bold text-slate-700 uppercase tracking-wider mb-1">
                  2. What is the verified correct answer?
                </label>
                <textarea
                  rows={4}
                  required
                  placeholder="Provide the exact, accurate factual answer. Example: Yes, you can exchange a product within 7 days. Please bring your purchase bill and original packaging."
                  value={correctAnswer}
                  onChange={(e) => setCorrectAnswer(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl border border-slate-300 text-xs focus:ring-2 focus:ring-blue-500 focus:outline-none leading-relaxed"
                />
              </div>

              <div className="p-3 rounded-xl bg-purple-50 border border-purple-200 text-[11px] text-purple-900 flex items-start space-x-2">
                <Sparkles className="w-4 h-4 text-purple-600 shrink-0 mt-0.5" />
                <span>
                  <strong>Knowledge Reinforcement:</strong> This correct answer will be saved directly into your shop's Knowledge Base under <em>AI Corrections</em>. Future customer questions about this will immediately receive your accurate answer!
                </span>
              </div>

              <div className="flex items-center justify-end space-x-3 pt-2">
                <button
                  type="button"
                  onClick={() => setBadModalItem(null)}
                  className="px-4 py-2 rounded-xl border border-slate-200 text-slate-600 text-xs font-semibold hover:bg-slate-50 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-5 py-2 rounded-xl bg-purple-600 text-white font-bold text-xs hover:bg-purple-700 transition shadow-sm disabled:opacity-50 flex items-center space-x-1.5"
                >
                  {submitting ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>Saving to Knowledge Base...</span>
                    </>
                  ) : (
                    <span>Save Correct Answer to Knowledge Base</span>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default RateAnswersPage;


