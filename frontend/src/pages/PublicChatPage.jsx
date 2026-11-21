import React, { useState, useEffect, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { customerApi } from '../services/api';
import { 
  Bot, 
  Send, 
  Store, 
  User, 
  Mail, 
  Sparkles, 
  Clock, 
  AlertCircle, 
  CheckCircle2, 
  Loader2, 
  HelpCircle, 
  ShieldCheck, 
  MessageSquare,
  ThumbsUp,
  ThumbsDown,
  Check,
  RotateCcw
} from 'lucide-react';

const PublicChatPage = () => {
  const { slug } = useParams();

  const [shop, setShop] = useState(null);
  const [shopLoading, setShopLoading] = useState(true);
  const [shopError, setShopError] = useState('');

  // Customer session state
  const [sessionToken, setSessionToken] = useState(() => {
    return localStorage.getItem(`shopfaq_session_${slug}`) || null;
  });
  const [customer, setCustomer] = useState(() => {
    const saved = localStorage.getItem(`shopfaq_cust_${slug}`);
    return saved ? JSON.parse(saved) : null;
  });

  // Modal form for new customer
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [email, setEmail] = useState('');
  const [sessionLoading, setSessionLoading] = useState(false);
  const [sessionError, setSessionError] = useState('');

  // Chat state
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [ownerFeedbackMap, setOwnerFeedbackMap] = useState({});

  const messagesEndRef = useRef(null);
  const isStreamingRef = useRef(false);
  const abortControllerRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  // 1. Fetch public shop profile
  useEffect(() => {
    const fetchShop = async () => {
      setShopLoading(true);
      try {
        const res = await customerApi.getShop(slug);
        if (res.data?.success) {
          setShop(res.data.data.shop);
        } else {
          setShopError(res.data?.message || 'Shop not found');
        }
      } catch (err) {
        setShopError(err.response?.data?.message || 'Shop not found. Please check URL.');
      } finally {
        setShopLoading(false);
      }
    };
    fetchShop();
  }, [slug]);

  // 2. Validate existing session & load previous messages
  useEffect(() => {
    let intervalId = null;

    const validateExistingSession = async (silent = false) => {
      if (!sessionToken || !slug) return;
      if (isStreamingRef.current) return; // Skip updating messages while streaming is in progress
      try {
        const res = await customerApi.validateSession(slug, sessionToken);
        if (res.data?.success && res.data.data.valid) {
          if (!silent) {
            setCustomer(res.data.data.customer);
            localStorage.setItem(`shopfaq_cust_${slug}`, JSON.stringify(res.data.data.customer));
          }
          if (res.data.data.messages && res.data.data.messages.length > 0) {
            const loadedOwnerFeedback = {};
            const msgs = res.data.data.messages.map(m => {
              if (m.sender_type === 'owner' && m.feedback_type) {
                loadedOwnerFeedback[m.id] = {
                  type: m.feedback_type,
                  submitted: true
                };
              }
              const isFallback = m.sender_type === 'ai' && (m.message_content?.includes("The shop owner will reply") || m.is_pending);
              return {
                id: m.id,
                sender: m.sender_type,
                text: m.message_content,
                questionId: m.question_id,
                isPendingFallback: isFallback,
                time: new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
              };
            });
            setMessages(msgs);
            if (Object.keys(loadedOwnerFeedback).length > 0) {
              setOwnerFeedbackMap(prev => ({ ...prev, ...loadedOwnerFeedback }));
            }
          }
        }
      } catch (err) {
        if (!silent) {
          console.warn("Existing customer session expired. Re-prompting for customer details.");
          localStorage.removeItem(`shopfaq_session_${slug}`);
          localStorage.removeItem(`shopfaq_cust_${slug}`);
          setSessionToken(null);
          setCustomer(null);
        }
      }
    };

    if (shop && sessionToken) {
      validateExistingSession(false);
      // Poll every 5s for new replies from shop owner
      intervalId = setInterval(() => {
        validateExistingSession(true);
      }, 5000);
    }

    return () => {
      if (intervalId) clearInterval(intervalId);
      if (abortControllerRef.current) abortControllerRef.current.abort();
    };
  }, [shop, slug, sessionToken]);

  // Handle customer registration form
  const handleStartChat = async (e) => {
    e.preventDefault();
    setSessionError('');
    setSessionLoading(true);

    try {
      const res = await customerApi.createSession(slug, {
        first_name: firstName,
        last_name: lastName,
        email: email
      });

      if (res.data?.success) {
        const { session_token, customer: custData } = res.data.data;
        setSessionToken(session_token);
        setCustomer(custData);
        localStorage.setItem(`shopfaq_session_${slug}`, session_token);
        localStorage.setItem(`shopfaq_cust_${slug}`, JSON.stringify(custData));

        // Add welcome greeting
        setMessages([
          {
            id: 'welcome',
            sender: 'ai',
            text: `Hello ${custData.first_name}! Welcome to ${shop?.shop_name}. How can I help you today? Ask any questions about our timings, products, policies, or services.`,
            time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
          }
        ]);
      } else {
        setSessionError(res.data?.message || 'Failed to establish session.');
      }
    } catch (err) {
      setSessionError(err.response?.data?.message || 'Could not start chat session. Please verify email.');
    } finally {
      setSessionLoading(false);
    }
  };

  // Send message (real-time streaming with progressive chunks)
  const handleSendMessage = async (e, retryText = null) => {
    if (e) e.preventDefault();
    const queryToSend = (retryText || inputMessage).trim();
    if (!queryToSend || isTyping) return;

    const userText = queryToSend;
    const nowTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    // Append customer message immediately (unless retrying the previous message directly)
    if (!retryText) {
      const tempUserMsg = {
        id: `cust_${Date.now()}`,
        sender: 'customer',
        text: userText,
        time: nowTime
      };
      setMessages((prev) => [...prev, tempUserMsg]);
      setInputMessage('');
    }

    setIsTyping(true);
    isStreamingRef.current = true;

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    const streamMsgId = `ai_stream_${Date.now()}`;
    let hasReceivedFirstChunk = false;
    let accumulatedText = '';

    try {
      await customerApi.sendChatStream(
        slug,
        sessionToken,
        userText,
        {
          onStart: () => {
            // Stream connection opened
          },
          onChunk: (chunkText) => {
            if (!chunkText) return;
            accumulatedText += chunkText;
            if (!hasReceivedFirstChunk) {
              hasReceivedFirstChunk = true;
              setIsTyping(false); // Hide typing dots, show progressive answer bubble
              setMessages((prev) => [
                ...prev,
                {
                  id: streamMsgId,
                  sender: 'ai',
                  text: accumulatedText,
                  isStreaming: true,
                  time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                }
              ]);
            } else {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === streamMsgId ? { ...m, text: accumulatedText } : m
                )
              );
            }
          },
          onDone: (data) => {
            isStreamingRef.current = false;
            setIsTyping(false);
            const finalAnswer = (data.answer && data.answer.trim())
              ? data.answer.trim()
              : (accumulatedText.trim() || "Thank you! The shop owner will reply to you soon by email.");
            const isFallback = !data.can_answer || finalAnswer.includes("The shop owner will reply to you soon by email.");

            if (!hasReceivedFirstChunk) {
              hasReceivedFirstChunk = true;
              setMessages((prev) => [
                ...prev,
                {
                  id: data.message_id || streamMsgId,
                  sender: 'ai',
                  text: finalAnswer,
                  isStreaming: false,
                  isPendingFallback: isFallback,
                  questionId: data.question_id,
                  time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                }
              ]);
            } else {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === streamMsgId
                    ? {
                        ...m,
                        id: data.message_id || m.id,
                        text: finalAnswer,
                        isStreaming: false,
                        isPendingFallback: isFallback,
                        questionId: data.question_id
                      }
                    : m
                )
              );
            }
          },
          onError: (errData) => {
            console.error("Stream error received:", errData);
            isStreamingRef.current = false;
            setIsTyping(false);
            if (!hasReceivedFirstChunk) {
              const errorMsg = {
                id: `err_${Date.now()}`,
                sender: 'ai',
                text: 'We encountered a momentary connection error. You can retry your question below.',
                isError: true,
                failedQuery: userText,
                time: nowTime
              };
              setMessages((prev) => [...prev, errorMsg]);
            }
          }
        },
        abortControllerRef.current.signal
      );
    } catch (err) {
      if (err.name === 'AbortError') {
        return; // Cleanup on abort
      }
      isStreamingRef.current = false;
      setIsTyping(false);

      if (err.response?.data?.errors?.requires_reauth || err.response?.status === 401) {
        localStorage.removeItem(`shopfaq_session_${slug}`);
        setSessionToken(null);
      } else {
        if (!hasReceivedFirstChunk) {
          const errorMsg = {
            id: `err_${Date.now()}`,
            sender: 'ai',
            text: 'We encountered a momentary connection error. You can retry your question below.',
            isError: true,
            failedQuery: userText,
            time: nowTime
          };
          setMessages((prev) => [...prev, errorMsg]);
        }
      }
    } finally {
      isStreamingRef.current = false;
      setIsTyping(false);
    }
  };

  // Handle customer feedback for shop owner replies (👍 Good / 👎 Bad)
  const handleOwnerFeedback = async (messageId, type) => {
    if (!messageId || !sessionToken) return;
    if (ownerFeedbackMap[messageId]?.submitted) return; // One-time feedback enforcement

    const previousFeedback = ownerFeedbackMap[messageId];

    // Optimistically update owner feedback state
    setOwnerFeedbackMap((prev) => ({
      ...prev,
      [messageId]: {
        type,
        submitted: false,
        submitting: true,
        error: null,
      }
    }));

    try {
      const res = await customerApi.submitOwnerFeedback(slug, sessionToken, {
        message_id: messageId,
        feedback_type: type
      });
      if (!res.data?.success) {
        throw new Error(res.data?.message || 'Failed to submit feedback');
      }
      setOwnerFeedbackMap((prev) => ({
        ...prev,
        [messageId]: {
          type,
          submitted: true,
          submitting: false,
          error: null,
        }
      }));
    } catch (err) {
      console.error("Failed to submit owner reply feedback:", err);
      const isAlreadySubmitted = err.response?.status === 409;
      setOwnerFeedbackMap((prev) => ({
        ...prev,
        [messageId]: {
          type: isAlreadySubmitted ? (err.response?.data?.errors?.existing_feedback || type) : (previousFeedback?.type || null),
          submitted: isAlreadySubmitted ? true : (previousFeedback?.submitted || false),
          submitting: false,
          error: isAlreadySubmitted ? 'Feedback has already been submitted for this reply.' : (err.response?.data?.message || 'Failed to submit feedback. Please try again.'),
        }
      }));
    }
  };

  // Loading shop state
  if (shopLoading) {
    return (
      <div className="min-h-screen bg-slate-100 flex items-center justify-center p-4">
        <div className="flex flex-col items-center space-y-3">
          <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
          <p className="text-sm font-semibold text-slate-600">Connecting to Shop Chatbot...</p>
        </div>
      </div>
    );
  }

  // Shop error state (404)
  if (shopError || !shop) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
        <div className="bg-white p-8 rounded-2xl border border-slate-200 max-w-md w-full text-center shadow-sm">
          <div className="w-12 h-12 rounded-full bg-red-100 text-red-600 flex items-center justify-center mx-auto mb-4">
            <AlertCircle className="w-6 h-6" />
          </div>
          <h2 className="text-xl font-bold text-slate-900">Shop Not Found</h2>
          <p className="mt-2 text-sm text-slate-600 leading-relaxed">
            The shop slug <code className="bg-slate-100 px-1.5 py-0.5 rounded text-red-600 font-mono text-xs font-bold">{slug}</code> does not exist or has been modified.
          </p>
          <Link
            to="/"
            className="mt-6 inline-flex items-center justify-center w-full py-2.5 px-4 rounded-xl bg-blue-600 text-white font-semibold text-sm hover:bg-blue-700 transition"
          >
            Go to Shop FAQ Bot Home
          </Link>
        </div>
      </div>
    );
  }

  const shopInitial = shop.shop_name ? shop.shop_name.charAt(0).toUpperCase() : 'S';

  return (
    <div className="min-h-screen bg-slate-100 flex flex-col items-center justify-center p-2 sm:p-4">
      {/* Main Chat Container */}
      <div className="w-full max-w-2xl bg-white rounded-2xl shadow-xl border border-slate-200 flex flex-col h-[94vh] sm:h-[88vh] overflow-hidden">
        
        {/* Chatbot Header */}
        <header className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white px-5 py-4 flex items-center justify-between shrink-0 shadow-sm">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-white/20 backdrop-blur-md flex items-center justify-center text-white font-black text-lg border border-white/30 shadow-inner">
              {shopInitial}
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h1 className="font-bold text-base tracking-tight leading-none">{shop.shop_name}</h1>
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              </div>
              <p className="text-xs text-blue-100 mt-1 flex items-center space-x-1">
                <Bot className="w-3.5 h-3.5" />
                <span>AI Customer Assistant</span>
              </p>
            </div>
          </div>

          <div className="text-right">
            <span className="text-[10px] font-mono uppercase tracking-wider bg-white/10 px-2 py-1 rounded border border-white/20">
              /s/{shop.slug}
            </span>
          </div>
        </header>

        {/* Customer Onboarding Modal (if no 36-hr session) */}
        {!sessionToken ? (
          <div className="flex-1 flex items-center justify-center p-6 bg-slate-50/70">
            <div className="bg-white p-6 sm:p-8 rounded-2xl border border-slate-200 shadow-md max-w-md w-full">
              <div className="w-12 h-12 rounded-xl bg-blue-100 text-blue-600 flex items-center justify-center mx-auto mb-4">
                <MessageSquare className="w-6 h-6" />
              </div>
              <h2 className="text-xl font-bold text-slate-900 text-center">Welcome to {shop.shop_name}!</h2>
              <p className="mt-1 text-xs text-slate-500 text-center">
                Please enter your details once to start chatting. You won't be asked again for 36 hours.
              </p>

              {sessionError && (
                <div className="mt-4 p-3 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs flex items-center space-x-2">
                  <AlertCircle className="w-4 h-4 shrink-0 text-red-500" />
                  <span>{sessionError}</span>
                </div>
              )}

              <form onSubmit={handleStartChat} className="mt-5 space-y-4">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[11px] font-bold text-slate-700 uppercase mb-1">First Name</label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. John"
                      value={firstName}
                      onChange={(e) => setFirstName(e.target.value)}
                      className="w-full px-3 py-2 rounded-lg border border-slate-300 text-xs focus:ring-2 focus:ring-blue-500 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-bold text-slate-700 uppercase mb-1">Last Name</label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. Doe"
                      value={lastName}
                      onChange={(e) => setLastName(e.target.value)}
                      className="w-full px-3 py-2 rounded-lg border border-slate-300 text-xs focus:ring-2 focus:ring-blue-500 focus:outline-none"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-slate-700 uppercase mb-1">Email Address</label>
                  <input
                    type="email"
                    required
                    placeholder="john@example.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-slate-300 text-xs focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  />
                  <span className="block text-[10px] text-slate-400 mt-1">
                    Used to email you if the shop owner answers a custom inquiry.
                  </span>
                </div>

                <button
                  type="submit"
                  disabled={sessionLoading}
                  className="w-full py-2.5 px-4 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs transition shadow-md shadow-blue-500/20 flex items-center justify-center space-x-2 disabled:opacity-50"
                >
                  {sessionLoading ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>Starting Chat...</span>
                    </>
                  ) : (
                    <span>Start Chatting</span>
                  )}
                </button>
              </form>
            </div>
          </div>
        ) : (
          /* Active Chat Conversation Area */
          <>
            {/* Session Info Banner */}
            <div className="bg-blue-50/70 border-b border-blue-100 px-4 py-1.5 flex items-center justify-between text-[11px] text-blue-700 shrink-0">
              <div className="flex items-center space-x-1.5 truncate">
                <User className="w-3.5 h-3.5 text-blue-600" />
                <span className="font-semibold">{customer?.full_name || `${customer?.first_name} ${customer?.last_name}`}</span>
                <span className="text-blue-400">({customer?.email})</span>
              </div>
              <div className="flex items-center space-x-1 text-slate-400 text-[10px] shrink-0">
                <Clock className="w-3 h-3" />
                <span>36h active session</span>
              </div>
            </div>

            {/* Messages Feed */}
            <div className="flex-1 p-4 sm:p-5 overflow-y-auto space-y-4 bg-slate-50/40">
              {messages.length === 0 && (
                <div className="text-center py-12 px-4">
                  <div className="w-12 h-12 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center mx-auto mb-3">
                    <Sparkles className="w-6 h-6" />
                  </div>
                  <h3 className="text-sm font-bold text-slate-800">Welcome to {shop.shop_name}!</h3>
                  <p className="text-xs text-slate-500 max-w-xs mx-auto mt-1">
                    Ask any question about our shop hours, products, services, or policies below.
                  </p>
                </div>
              )}

              {messages.map((msg, index) => {
                const isCust = msg.sender === 'customer';
                const isOwner = msg.sender === 'owner';
                const isAi = msg.sender === 'ai';

                return (
                  <div
                    key={msg.id || index}
                    className={`flex items-end space-x-2 ${isCust ? 'justify-end' : 'justify-start'}`}
                  >
                    {!isCust && (
                      isOwner ? (
                        <div className="w-7 h-7 rounded-lg bg-indigo-600 text-white text-xs font-bold flex items-center justify-center shrink-0 shadow-sm" title="Shop Owner">
                          <Store className="w-4 h-4" />
                        </div>
                      ) : (
                        <div className="w-7 h-7 rounded-lg bg-blue-600 text-white text-xs font-bold flex items-center justify-center shrink-0">
                          {shopInitial}
                        </div>
                      )
                    )}
                    <div className={`max-w-[85%] sm:max-w-[80%] rounded-2xl px-4 py-2.5 shadow-sm text-sm ${
                      isCust 
                        ? 'bg-blue-600 text-white rounded-br-none'
                        : isOwner
                          ? 'bg-indigo-50/70 border border-indigo-200/90 text-slate-900 rounded-bl-none'
                          : msg.isError
                            ? 'bg-red-50 border border-red-200 text-red-900 rounded-bl-none'
                            : msg.isPendingFallback
                              ? 'bg-amber-50 border border-amber-200 text-amber-900 rounded-bl-none'
                              : 'bg-white border border-slate-200/80 text-slate-800 rounded-bl-none'
                    }`}>
                      {isOwner && (
                        <div className="flex items-center space-x-1.5 mb-1.5">
                          <span className="text-[10px] font-bold text-indigo-700 bg-indigo-100/90 px-2 py-0.5 rounded-md uppercase tracking-wider inline-flex items-center space-x-1">
                            <Store className="w-3 h-3" />
                            <span>Shop Owner</span>
                          </span>
                        </div>
                      )}
                      <p className="whitespace-pre-wrap leading-relaxed">
                        {msg.text || (msg.isStreaming ? "" : "Thank you! The shop owner will reply to you soon by email.")}
                        {msg.isStreaming && (
                          <span className="inline-block w-1.5 h-3.5 bg-blue-600 ml-1 translate-y-0.5 animate-pulse" />
                        )}
                      </p>

                      {/* Customer Feedback for Shop Owner Replies */}
                      {isOwner && (
                        <div className="mt-2.5 pt-2 border-t border-indigo-100 flex flex-col space-y-1.5">
                          <span className="text-[11px] text-slate-600 font-medium">Was this response helpful?</span>
                          <div className="flex flex-wrap items-center gap-1.5">
                            <button
                              type="button"
                              disabled={ownerFeedbackMap[msg.id]?.submitted || ownerFeedbackMap[msg.id]?.submitting}
                              onClick={() => handleOwnerFeedback(msg.id, 'good')}
                              className={`inline-flex items-center space-x-1 px-2.5 py-1 rounded-lg text-[11px] font-semibold transition border ${
                                ownerFeedbackMap[msg.id]?.type === 'good'
                                  ? 'bg-emerald-50 text-emerald-700 border-emerald-300 font-bold shadow-xs'
                                  : ownerFeedbackMap[msg.id]?.submitted
                                  ? 'bg-slate-50 text-slate-400 border-slate-200 opacity-60 cursor-not-allowed'
                                  : 'bg-white hover:bg-slate-50 text-slate-600 border-slate-200'
                              }`}
                            >
                              <ThumbsUp className="w-3 h-3" />
                              <span>👍 Good</span>
                            </button>

                            <button
                              type="button"
                              disabled={ownerFeedbackMap[msg.id]?.submitted || ownerFeedbackMap[msg.id]?.submitting}
                              onClick={() => handleOwnerFeedback(msg.id, 'bad')}
                              className={`inline-flex items-center space-x-1 px-2.5 py-1 rounded-lg text-[11px] font-semibold transition border ${
                                ownerFeedbackMap[msg.id]?.type === 'bad'
                                  ? 'bg-rose-50 text-rose-700 border-rose-300 font-bold shadow-xs'
                                  : ownerFeedbackMap[msg.id]?.submitted
                                  ? 'bg-slate-50 text-slate-400 border-slate-200 opacity-60 cursor-not-allowed'
                                  : 'bg-white hover:bg-slate-50 text-slate-600 border-slate-200'
                              }`}
                            >
                              <ThumbsDown className="w-3 h-3" />
                              <span>👎 Bad</span>
                            </button>

                            {ownerFeedbackMap[msg.id]?.submitted && !ownerFeedbackMap[msg.id]?.error && (
                              <span className="text-[11px] text-emerald-600 font-medium flex items-center space-x-1 animate-fade-in ml-1">
                                <Check className="w-3 h-3" />
                                <span>Thank you for your feedback!</span>
                              </span>
                            )}

                            {ownerFeedbackMap[msg.id]?.error && (
                              <span className="text-[11px] text-rose-600 font-medium ml-1">
                                {ownerFeedbackMap[msg.id].error}
                              </span>
                            )}
                          </div>
                        </div>
                      )}

                      {/* Retry Button on connection / processing errors */}
                      {msg.isError && msg.failedQuery && (
                        <div className="mt-2 pt-1 border-t border-red-200/60">
                          <button
                            type="button"
                            onClick={() => handleSendMessage(null, msg.failedQuery)}
                            disabled={isTyping}
                            className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-lg bg-red-100 hover:bg-red-200 text-red-800 text-[11px] font-semibold transition disabled:opacity-50"
                          >
                            <RotateCcw className="w-3 h-3" />
                            <span>Retry Question</span>
                          </button>
                        </div>
                      )}

                      <span className={`block text-[10px] mt-1 text-right ${
                        isCust ? 'text-blue-200' : 'text-slate-400'
                      }`}>
                        {msg.time}
                      </span>
                    </div>
                  </div>
                );
              })}

              {/* Typing Indicator */}
              {isTyping && (
                <div className="flex items-end space-x-2 justify-start">
                  <div className="w-7 h-7 rounded-lg bg-blue-600 text-white text-xs font-bold flex items-center justify-center shrink-0">
                    {shopInitial}
                  </div>
                  <div className="bg-white border border-slate-200 rounded-2xl rounded-bl-none px-4 py-3 shadow-sm flex items-center space-x-1.5">
                    <span className="dot-pulse bg-blue-600"></span>
                    <span className="dot-pulse bg-blue-600"></span>
                    <span className="dot-pulse bg-blue-600"></span>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Chat Input Bar */}
            <form onSubmit={handleSendMessage} className="p-3 bg-white border-t border-slate-200 flex items-center space-x-2 shrink-0">
              <input
                type="text"
                placeholder="Ask a question about timings, products, returns..."
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                disabled={isTyping}
                className="flex-1 px-4 py-2.5 rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
              />
              <button
                type="submit"
                disabled={!inputMessage.trim() || isTyping}
                className="p-2.5 rounded-xl bg-blue-600 text-white hover:bg-blue-700 transition disabled:opacity-40 shadow-sm shadow-blue-500/20"
              >
                <Send className="w-5 h-5" />
              </button>
            </form>
          </>
        )}
      </div>

      {/* Footer Branding */}
      <div className="mt-3 text-center text-xs text-slate-400 flex items-center justify-center space-x-2">
        <ShieldCheck className="w-3.5 h-3.5 text-slate-400" />
        <span>Powered by <strong>Shop FAQ Bot</strong> &bull; Multi-Tenant AI Platform</span>
      </div>
    </div>
  );
};

export default PublicChatPage;

