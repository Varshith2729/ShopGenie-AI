import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { questionsApi, emailApi } from '../../services/api';
import { 
  HelpCircle, 
  Send, 
  Mail, 
  CheckCircle, 
  Clock, 
  AlertCircle, 
  RotateCw, 
  X, 
  Loader2, 
  Sparkles, 
  User, 
  Calendar,
  AlertTriangle,
  CheckCheck,
  Bot,
  MessageSquare
} from 'lucide-react';

const QuestionsPage = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialStatus = searchParams.get('status') || '';

  const [questions, setQuestions] = useState([]);
  const [statusFilter, setStatusFilter] = useState(initialStatus);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);

  // Answer modal
  const [selectedQuestion, setSelectedQuestion] = useState(null);
  const [answerText, setAnswerText] = useState('');
  const [forceResend, setForceResend] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [notification, setNotification] = useState(null);
  const [retryingEmailId, setRetryingEmailId] = useState(null);

  const fetchQuestions = async () => {
    setLoading(true);
    try {
      const res = await questionsApi.list({ status: statusFilter || undefined });
      if (res.data?.success) {
        setQuestions(res.data.data.questions || []);
      }
    } catch (err) {
      console.error("Failed to load questions", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQuestions();
  }, [statusFilter]);

  const handleFilterChange = (status) => {
    setStatusFilter(status);
    if (status) {
      setSearchParams({ status });
    } else {
      setSearchParams({});
    }
  };

  const handleSyncEmails = async () => {
    setSyncing(true);
    try {
      const res = await emailApi.syncInbox();
      if (res.data?.success) {
        setNotification({
          type: 'success',
          message: res.data.message || 'Gmail inbox synced successfully!'
        });
        fetchQuestions();
      }
    } catch (err) {
      setNotification({
        type: 'error',
        message: err.response?.data?.message || 'Failed to sync Gmail inbox. Check Gmail credentials in .env.'
      });
    } finally {
      setSyncing(false);
      setTimeout(() => setNotification(null), 5000);
    }
  };

  const openAnswerModal = async (q) => {
    setSelectedQuestion(q);
    setAnswerText(q.status === 'customer_replied' ? '' : (q.owner_answer || ''));
    setForceResend(false);
    setError('');

    // Fetch latest question details with messages thread
    try {
      const res = await questionsApi.get(q.id);
      if (res.data?.success) {
        setSelectedQuestion(res.data.data);
      }
    } catch (err) {
      console.error("Failed to fetch fresh question details:", err);
    }
  };

  const handleSendAnswer = async (e) => {
    e.preventDefault();
    if (!answerText.trim()) {
      setError('Please provide an answer or follow-up response.');
      return;
    }

    setSubmitting(true);
    setError('');

    try {
      let res;
      if (selectedQuestion.status === 'customer_replied' || (selectedQuestion.messages && selectedQuestion.messages.length > 2)) {
        // Send follow-up reply in two-way thread
        res = await questionsApi.sendFollowUp(selectedQuestion.id, answerText.trim());
      } else {
        res = await questionsApi.answer(selectedQuestion.id, answerText.trim(), {
          force_resend: forceResend
        });
      }

      if (res.data?.success) {
        const emailStatus = res.data.data?.email_status;
        const emailError = res.data.data?.email_error;

        if (emailStatus === 'sent') {
          setNotification({
            type: 'success',
            message: 'Your reply has been saved and the email notification has been submitted successfully to the customer.'
          });
        } else if (emailStatus === 'failed') {
          setNotification({
            type: 'warning',
            message: `Your reply has been saved, but the email notification could not be sent. Please retry. (${emailError || 'Provider rejected request'})`
          });
        } else {
          setNotification({
            type: 'info',
            message: res.data.message || 'Your reply has been saved.'
          });
        }

        setSelectedQuestion(null);
        setAnswerText('');
        fetchQuestions();
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to submit answer.');
    } finally {
      setSubmitting(false);
      setTimeout(() => setNotification(null), 7000);
    }
  };

  const handleRetryEmail = async (qId, force = false) => {
    setRetryingEmailId(qId);
    try {
      const res = await questionsApi.retryEmail(qId, force);
      if (res.data?.success) {
        setNotification({
          type: 'success',
          message: 'Email notification has been submitted successfully to the customer!'
        });
        if (selectedQuestion && selectedQuestion.id === qId) {
          setSelectedQuestion({ ...selectedQuestion, email_status: 'sent', email_error: null });
        }
        fetchQuestions();
      }
    } catch (err) {
      const errMsg = err.response?.data?.message || err.response?.data?.errors?.email_error || 'Failed to resend email';
      setNotification({
        type: 'error',
        message: errMsg
      });
      fetchQuestions();
    } finally {
      setRetryingEmailId(null);
      setTimeout(() => setNotification(null), 7000);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight">Customer Questions</h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            Review customer inquiries and two-way email conversations. Answer pending questions to notify customers and reinforce your AI knowledge base.
          </p>
        </div>

        {/* Action Controls: Sync Gmail + Filter Pills */}
        <div className="flex flex-wrap items-center gap-2 self-start sm:self-auto">
          <button
            onClick={handleSyncEmails}
            disabled={syncing}
            className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-purple-50 hover:bg-purple-100 text-purple-700 border border-purple-200 text-xs font-bold transition shadow-xs disabled:opacity-50"
            title="Check Gmail for customer email replies"
          >
            <RotateCw className={`w-3.5 h-3.5 ${syncing ? 'animate-spin text-purple-600' : ''}`} />
            <span>{syncing ? 'Checking Gmail...' : 'Sync Email Replies'}</span>
          </button>

          <div className="flex items-center space-x-1 bg-white p-1 rounded-xl border border-slate-200 shadow-xs">
            <button
              onClick={() => handleFilterChange('')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                !statusFilter ? 'bg-blue-600 text-white' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              All
            </button>
            <button
              onClick={() => handleFilterChange('pending')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                statusFilter === 'pending' ? 'bg-amber-600 text-white' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Pending
            </button>
            <button
              onClick={() => handleFilterChange('customer_replied')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition flex items-center space-x-1 ${
                statusFilter === 'customer_replied' ? 'bg-purple-600 text-white' : 'text-purple-700 hover:bg-purple-50'
              }`}
            >
              <Mail className="w-3 h-3" />
              <span>Customer Replied</span>
            </button>
            <button
              onClick={() => handleFilterChange('answered')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                statusFilter === 'answered' ? 'bg-emerald-600 text-white' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Answered
            </button>
          </div>
        </div>
      </div>

      {/* Notification Toast */}
      {notification && (
        <div className={`p-4 rounded-xl text-xs font-semibold flex items-start space-x-3 transition shadow-sm ${
          notification.type === 'success' 
            ? 'bg-emerald-50 border border-emerald-200 text-emerald-900'
            : notification.type === 'warning'
              ? 'bg-amber-50 border border-amber-200 text-amber-900'
              : 'bg-rose-50 border border-rose-200 text-rose-900'
        }`}>
          {notification.type === 'success' && <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />}
          {notification.type === 'warning' && <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />}
          {notification.type === 'error' && <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />}
          <span className="leading-relaxed">{notification.message}</span>
        </div>
      )}

      {/* Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        {loading ? (
          <div className="flex flex-col items-center justify-center py-16 space-y-2">
            <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
            <p className="text-xs text-slate-500">Loading questions...</p>
          </div>
        ) : questions.length === 0 ? (
          <div className="text-center py-16 px-4">
            <HelpCircle className="w-10 h-10 text-slate-300 mx-auto mb-2" />
            <h3 className="text-sm font-bold text-slate-800">No questions found</h3>
            <p className="text-xs text-slate-500 mt-1">
              {statusFilter ? `No ${statusFilter.replace('_', ' ')} questions matching this filter.` : 'No customer inquiries yet.'}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 font-bold uppercase tracking-wider text-[10px]">
                  <th className="px-5 py-3.5">Customer</th>
                  <th className="px-5 py-3.5">Question / Latest Thread</th>
                  <th className="px-5 py-3.5">Date</th>
                  <th className="px-5 py-3.5">Status</th>
                  <th className="px-5 py-3.5">Email Delivery</th>
                  <th className="px-5 py-3.5 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {questions.map((q) => (
                  <tr key={q.id} className="hover:bg-slate-50/70 transition">
                    <td className="px-5 py-4 whitespace-nowrap">
                      <div className="font-bold text-slate-900">{q.customer_name}</div>
                      <div className="text-[11px] text-slate-400 font-mono">{q.customer_email}</div>
                    </td>
                    <td className="px-5 py-4 max-w-xs md:max-w-md">
                      <p className="font-semibold text-slate-800 text-xs">{q.question}</p>
                      {q.status === 'customer_replied' ? (
                        <p className="text-[11px] text-purple-700 mt-1 font-bold flex items-center space-x-1">
                          <Mail className="w-3 h-3 text-purple-600" />
                          <span>Customer replied via email &mdash; needs response</span>
                        </p>
                      ) : q.owner_answer ? (
                        <p className="text-[11px] text-emerald-700 mt-1">
                          <span className="font-bold">Owner:</span> {q.owner_answer}
                        </p>
                      ) : q.ai_answer ? (
                        <p className="text-[11px] text-blue-600 mt-1">
                          <span className="font-bold">AI:</span> {q.ai_answer}
                        </p>
                      ) : null}
                    </td>
                    <td className="px-5 py-4 whitespace-nowrap text-slate-500 text-[11px]">
                      {new Date(q.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-5 py-4 whitespace-nowrap">
                      {q.status === 'customer_replied' ? (
                        <span className="px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider bg-purple-100 text-purple-800 border border-purple-300 flex items-center space-x-1 w-max animate-pulse">
                          <Mail className="w-3 h-3" />
                          <span>Customer Replied</span>
                        </span>
                      ) : q.status === 'answered' ? (
                        <span className="px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider bg-emerald-50 text-emerald-700 border border-emerald-200">
                          Answered
                        </span>
                      ) : (
                        <span className="px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider bg-amber-50 text-amber-700 border border-amber-200">
                          Pending
                        </span>
                      )}
                    </td>
                    <td className="px-5 py-4 whitespace-nowrap">
                      {q.email_status === 'sent' && (
                        <div className="flex flex-col">
                          <span className="inline-flex items-center space-x-1 text-emerald-600 text-[11px] font-bold">
                            <CheckCheck className="w-3.5 h-3.5" />
                            <span>Accepted by Provider</span>
                          </span>
                          {q.email_sent_at && (
                            <span className="text-[10px] text-slate-400">
                              {new Date(q.email_sent_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </span>
                          )}
                        </div>
                      )}
                      {q.email_status === 'failed' && (
                        <div className="flex items-center space-x-2">
                          <div className="flex flex-col">
                            <span className="text-rose-600 text-[11px] font-bold inline-flex items-center space-x-1">
                              <AlertCircle className="w-3.5 h-3.5" />
                              <span>Delivery Failed</span>
                            </span>
                            {q.email_error && (
                              <span className="text-[10px] text-slate-400 max-w-[140px] truncate" title={q.email_error}>
                                {q.email_error}
                              </span>
                            )}
                          </div>
                          <button
                            onClick={() => handleRetryEmail(q.id)}
                            disabled={retryingEmailId === q.id}
                            className="p-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-100 text-blue-600 shadow-sm transition"
                            title="Retry sending email"
                          >
                            <RotateCw className={`w-3.5 h-3.5 ${retryingEmailId === q.id ? 'animate-spin text-blue-600' : ''}`} />
                          </button>
                        </div>
                      )}
                      {q.email_status === 'pending' && (
                        <span className="text-amber-600 text-[11px] font-medium flex items-center space-x-1">
                          <Clock className="w-3 h-3" />
                          <span>Waiting for Reply</span>
                        </span>
                      )}
                      {q.email_status === 'not_applicable' && (
                        <span className="text-slate-400 text-[11px]">N/A (AI answered)</span>
                      )}
                    </td>
                    <td className="px-5 py-4 whitespace-nowrap text-right">
                      <button
                        onClick={() => openAnswerModal(q)}
                        className={`inline-flex items-center space-x-1 px-3 py-1.5 rounded-lg text-xs font-bold transition shadow-sm ${
                          q.status === 'customer_replied'
                            ? 'bg-purple-600 hover:bg-purple-700 text-white shadow-purple-500/20'
                            : q.status === 'pending'
                              ? 'bg-blue-600 hover:bg-blue-700 text-white'
                              : 'bg-slate-100 hover:bg-slate-200 text-slate-700'
                        }`}
                      >
                        {q.status === 'customer_replied' ? (
                          <>
                            <Mail className="w-3 h-3" />
                            <span>Reply to Email</span>
                          </>
                        ) : q.status === 'pending' ? (
                          <>
                            <Send className="w-3 h-3" />
                            <span>Answer Now</span>
                          </>
                        ) : (
                          <>
                            <MessageSquare className="w-3 h-3" />
                            <span>View Thread / Edit</span>
                          </>
                        )}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Answer & Conversation Thread Modal */}
      {selectedQuestion && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-2xl w-full p-6 shadow-2xl border border-slate-200 max-h-[90vh] flex flex-col">
            <div className="flex items-center justify-between mb-3 shrink-0">
              <div className="flex items-center space-x-2">
                <div className={`w-8 h-8 rounded-xl flex items-center justify-center ${
                  selectedQuestion.status === 'customer_replied' ? 'bg-purple-100 text-purple-700' : 'bg-blue-100 text-blue-600'
                }`}>
                  {selectedQuestion.status === 'customer_replied' ? <Mail className="w-4 h-4" /> : <Send className="w-4 h-4" />}
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-900">
                    {selectedQuestion.status === 'customer_replied' 
                      ? 'Two-Way Conversation & Follow-Up Reply' 
                      : selectedQuestion.status === 'answered' 
                        ? 'Update Reply / Conversation Thread' 
                        : 'Reply to Customer Question'}
                  </h3>
                  <div className="text-[11px] text-slate-400">
                    Question #{selectedQuestion.id} &bull; {selectedQuestion.customer_name} ({selectedQuestion.customer_email})
                  </div>
                </div>
              </div>
              <button
                onClick={() => setSelectedQuestion(null)}
                className="p-1 text-slate-400 hover:text-slate-600 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Conversation History Thread Area */}
            <div className="flex-1 overflow-y-auto space-y-3 bg-slate-50/70 p-4 rounded-xl border border-slate-200 mb-4 text-xs">
              {/* Original Question */}
              <div className="bg-white p-3 rounded-xl border border-slate-200 shadow-xs">
                <div className="flex items-center justify-between text-[10px] text-slate-400 mb-1">
                  <span className="font-bold text-slate-600 uppercase">Original Customer Question</span>
                  <span>{new Date(selectedQuestion.created_at).toLocaleString()}</span>
                </div>
                <p className="font-semibold text-slate-900">{selectedQuestion.question}</p>
              </div>

              {/* Back-and-forth messages if present */}
              {selectedQuestion.messages && selectedQuestion.messages.length > 0 && (
                <div className="space-y-2.5 pt-2 border-t border-slate-200">
                  <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Conversation History:</div>
                  {selectedQuestion.messages.map((m, idx) => {
                    const isOwner = m.sender_type === 'owner';
                    const isAI = m.sender_type === 'ai';
                    const isCustomer = m.sender_type === 'customer';

                    return (
                      <div
                        key={m.id || idx}
                        className={`flex flex-col ${isOwner ? 'items-end' : 'items-start'}`}
                      >
                        <div className="flex items-center space-x-1.5 text-[10px] text-slate-400 mb-0.5">
                          {isOwner && <span className="font-bold text-blue-700">Shop Owner</span>}
                          {isAI && <span className="font-bold text-blue-600 flex items-center space-x-0.5"><Bot className="w-2.5 h-2.5" /><span>AI</span></span>}
                          {isCustomer && (
                            <span className="font-bold text-slate-700 flex items-center space-x-0.5">
                              {m.email_message_id ? <Mail className="w-2.5 h-2.5 text-purple-600" /> : <User className="w-2.5 h-2.5" />}
                              <span>Customer {m.email_message_id ? '(via Email Reply)' : ''}</span>
                            </span>
                          )}
                          <span>&bull;</span>
                          <span>{m.created_at ? new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''}</span>
                        </div>
                        <div className={`p-3 rounded-xl max-w-[85%] leading-relaxed ${
                          isOwner 
                            ? 'bg-blue-600 text-white rounded-br-none shadow-xs'
                            : isAI 
                              ? 'bg-blue-50 border border-blue-200 text-blue-900 rounded-bl-none'
                              : 'bg-white border border-slate-200 text-slate-800 rounded-bl-none shadow-xs'
                        }`}>
                          <p className="whitespace-pre-wrap">{m.message_content}</p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Email Status Indicator in Modal */}
            {selectedQuestion.email_status === 'failed' && (
              <div className="mb-3 p-2.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center justify-between shrink-0">
                <div className="flex items-center space-x-1.5">
                  <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
                  <span>Previous email delivery failed: {selectedQuestion.email_error || 'Provider rejected'}</span>
                </div>
                <button
                  type="button"
                  onClick={() => handleRetryEmail(selectedQuestion.id, true)}
                  disabled={retryingEmailId === selectedQuestion.id}
                  className="px-2.5 py-1 rounded bg-rose-600 hover:bg-rose-700 text-white font-bold text-[10px] transition shrink-0"
                >
                  Retry Email
                </button>
              </div>
            )}

            {error && (
              <div className="mb-3 p-3 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs flex items-center space-x-2 shrink-0">
                <AlertCircle className="w-4 h-4 shrink-0 text-red-500" />
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleSendAnswer} className="space-y-3 shrink-0">
              <div>
                <label className="block text-[11px] font-bold text-slate-700 uppercase tracking-wider mb-1">
                  {selectedQuestion.status === 'customer_replied' ? 'Your Follow-Up Response to Customer' : 'Your Official Answer'}
                </label>
                <textarea
                  rows={3}
                  required
                  placeholder="Type your message here. It will immediately be delivered to the customer's email inbox and stored in this conversation history."
                  value={answerText}
                  onChange={(e) => setAnswerText(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl border border-slate-300 text-xs focus:ring-2 focus:ring-blue-500 focus:outline-none leading-relaxed"
                />
              </div>

              <div className="flex items-center justify-between pt-1">
                <div className="text-[11px] text-slate-500 flex items-center space-x-1">
                  <Mail className="w-3.5 h-3.5 text-blue-600" />
                  <span>Recipient: <strong>{selectedQuestion.customer_email}</strong></span>
                </div>

                <div className="flex items-center space-x-2">
                  <button
                    type="button"
                    onClick={() => setSelectedQuestion(null)}
                    className="px-4 py-2 rounded-xl border border-slate-200 text-slate-600 text-xs font-semibold hover:bg-slate-50 transition"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submitting}
                    className="px-5 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs transition shadow-sm disabled:opacity-50 flex items-center space-x-1.5"
                  >
                    {submitting ? (
                      <>
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        <span>Sending...</span>
                      </>
                    ) : (
                      <>
                        <Send className="w-3.5 h-3.5" />
                        <span>Send Reply & Email Customer</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default QuestionsPage;
