import React, { useState, useEffect } from 'react';
import { feedbackApi } from '../../services/api';
import {
  ThumbsUp,
  ThumbsDown,
  Loader2,
  Store,
  Search,
  Percent,
  MessageSquare
} from 'lucide-react';

const RateAnswersPage = () => {
  const [items, setItems] = useState([]);
  const [stats, setStats] = useState({ total_good: 0, total_bad: 0, helpfulness_percentage: 0, total_rated: 0 });
  const [loading, setLoading] = useState(true);
  const [typeFilter, setTypeFilter] = useState('');
  const [searchQuery, setSearchQuery] = useState('');

  const fetchOwnerFeedback = async (silent = false) => {
    if (!silent) setLoading(true);
    try {
      const res = await feedbackApi.listOwnerReplies({
        type: typeFilter || undefined,
        q: searchQuery.trim() || undefined
      });
      if (res.data?.success) {
        setItems(res.data.data.items || []);
        setStats({
          total_good: res.data.data.total_good || 0,
          total_bad: res.data.data.total_bad || 0,
          total_rated: res.data.data.total_rated || 0,
          helpfulness_percentage: res.data.data.helpfulness_percentage || 0
        });
      }
    } catch (err) {
      console.error("Failed to load owner reply feedback", err);
    } finally {
      if (!silent) setLoading(false);
    }
  };

  useEffect(() => {
    fetchOwnerFeedback(false);

    const interval = setInterval(() => {
      fetchOwnerFeedback(true);
    }, 6000);

    return () => clearInterval(interval);
  }, [typeFilter, searchQuery]);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-black text-slate-900 tracking-tight">Customer Feedback</h1>
        <p className="text-xs sm:text-sm text-slate-500 mt-1">
          Review customer satisfaction ratings (👍 Good / 👎 Bad) on your direct email and chat replies.
        </p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm flex items-center space-x-4">
          <div className="w-12 h-12 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center font-bold">
            <ThumbsUp className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs font-bold text-slate-400 uppercase tracking-wider">Good Owner Replies</div>
            <div className="text-2xl font-black text-slate-900 mt-0.5">{stats.total_good}</div>
          </div>
        </div>

        <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm flex items-center space-x-4">
          <div className="w-12 h-12 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center font-bold">
            <ThumbsDown className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs font-bold text-slate-400 uppercase tracking-wider">Bad Owner Replies</div>
            <div className="text-2xl font-black text-slate-900 mt-0.5">{stats.total_bad}</div>
          </div>
        </div>

        <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm flex items-center space-x-4">
          <div className="w-12 h-12 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center font-bold">
            <Percent className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs font-bold text-slate-400 uppercase tracking-wider">Helpfulness Rate</div>
            <div className="text-2xl font-black text-indigo-600 mt-0.5">{stats.helpfulness_percentage}%</div>
          </div>
        </div>

        <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm flex items-center space-x-4">
          <div className="w-12 h-12 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center font-bold">
            <MessageSquare className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs font-bold text-slate-400 uppercase tracking-wider">Total Rated Replies</div>
            <div className="text-2xl font-black text-blue-600 mt-0.5">{stats.total_rated}</div>
          </div>
        </div>
      </div>

      {/* Search & Filters */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white p-3 rounded-2xl border border-slate-200 shadow-sm">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search question, owner reply, or customer..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 rounded-xl border border-slate-200 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        <div className="flex items-center space-x-1.5 self-start sm:self-auto">
          <button
            onClick={() => setTypeFilter('')}
            className={`px-3 py-1.5 rounded-xl text-xs font-bold transition ${
              !typeFilter ? 'bg-indigo-600 text-white shadow-xs' : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            All Replies
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

      {/* Owner Reply Feedback Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        {loading ? (
          <div className="flex flex-col items-center justify-center py-16 space-y-2">
            <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" />
            <p className="text-xs text-slate-500">Loading customer feedback...</p>
          </div>
        ) : items.length === 0 ? (
          <div className="text-center py-16 px-4">
            <Store className="w-10 h-10 text-slate-300 mx-auto mb-2" />
            <h3 className="text-sm font-bold text-slate-800">No Feedback Received Yet</h3>
            <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1">
              {typeFilter || searchQuery
                ? 'No owner replies match the current filter or search.'
                : 'When you answer customer questions and customers rate your responses with 👍 Good or 👎 Bad, their feedback will appear here.'}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 font-bold uppercase tracking-wider text-[10px]">
                  <th className="px-5 py-3.5">Customer</th>
                  <th className="px-5 py-3.5">Customer Question</th>
                  <th className="px-5 py-3.5">Your Owner Reply</th>
                  <th className="px-5 py-3.5">Customer Feedback</th>
                  <th className="px-5 py-3.5">Date & Time</th>
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
                      <p className="font-semibold text-slate-900 leading-snug">{item.question || '(In Conversation)'}</p>
                    </td>
                    <td className="px-5 py-4 max-w-xs md:max-w-md">
                      <div className="bg-indigo-50/70 p-3 rounded-xl border border-indigo-100 text-[11px] text-slate-800 leading-relaxed">
                        <span className="font-bold text-indigo-700 block mb-0.5 text-[10px] uppercase tracking-wider">
                          Shop Owner:
                        </span>
                        <p className="whitespace-pre-wrap">{item.owner_reply}</p>
                      </div>
                    </td>
                    <td className="px-5 py-4 whitespace-nowrap">
                      {item.feedback_type === 'good' ? (
                        <span className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 text-[11px] font-bold">
                          <ThumbsUp className="w-3.5 h-3.5" />
                          <span>👍 Good</span>
                        </span>
                      ) : (
                        <span className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-rose-50 text-rose-700 border border-rose-200 text-[11px] font-bold">
                          <ThumbsDown className="w-3.5 h-3.5" />
                          <span>👎 Bad</span>
                        </span>
                      )}
                    </td>
                    <td className="px-5 py-4 whitespace-nowrap text-slate-500 text-[11px]">
                      {item.created_at ? new Date(item.created_at).toLocaleString() : 'N/A'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default RateAnswersPage;
