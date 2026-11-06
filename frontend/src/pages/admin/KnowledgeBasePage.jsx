import React, { useState, useEffect } from 'react';
import { knowledgeApi } from '../../services/api';
import { 
  BookOpen, 
  Plus, 
  Search, 
  Filter, 
  Edit3, 
  Trash2, 
  AlertCircle, 
  CheckCircle2, 
  Loader2, 
  X,
  Sparkles,
  Tag
} from 'lucide-react';

const KnowledgeBasePage = () => {
  const [entries, setEntries] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');

  // Modals
  const [modalOpen, setModalOpen] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editingId, setEditingId] = useState(null);

  // Form fields
  const [title, setTitle] = useState('');
  const [category, setCategory] = useState('General');
  const [content, setContent] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState('');
  const [notification, setNotification] = useState('');

  const fetchKnowledge = async () => {
    setLoading(true);
    try {
      const res = await knowledgeApi.list({
        search: search.trim() || undefined,
        category: selectedCategory || undefined
      });
      if (res.data?.success) {
        setEntries(res.data.data.knowledge_entries || []);
        setCategories(res.data.data.categories || []);
      }
    } catch (err) {
      console.error("Failed to load knowledge entries", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchKnowledge();
  }, [selectedCategory]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    fetchKnowledge();
  };

  const openAddModal = () => {
    setIsEditing(false);
    setEditingId(null);
    setTitle('');
    setCategory('General');
    setContent('');
    setFormError('');
    setModalOpen(true);
  };

  const openEditModal = (entry) => {
    setIsEditing(true);
    setEditingId(entry.id);
    setTitle(entry.title);
    setCategory(entry.category || 'General');
    setContent(entry.content);
    setFormError('');
    setModalOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!title.trim() || !content.trim()) {
      setFormError('Title and content are required.');
      return;
    }

    setSubmitting(true);
    setFormError('');

    try {
      if (isEditing) {
        const res = await knowledgeApi.update(editingId, {
          title: title.trim(),
          category: category.trim(),
          content: content.trim()
        });
        if (res.data?.success) {
          setNotification('Knowledge entry updated successfully!');
          setModalOpen(false);
          fetchKnowledge();
        }
      } else {
        const res = await knowledgeApi.create({
          title: title.trim(),
          category: category.trim(),
          content: content.trim()
        });
        if (res.data?.success) {
          setNotification('New knowledge entry added successfully!');
          setModalOpen(false);
          fetchKnowledge();
        }
      }
    } catch (err) {
      setFormError(err.response?.data?.message || 'Failed to save entry');
    } finally {
      setSubmitting(false);
      setTimeout(() => setNotification(''), 3000);
    }
  };

  const handleDelete = async (id, entryTitle) => {
    if (!window.confirm(`Are you sure you want to delete "${entryTitle}"?`)) return;

    try {
      const res = await knowledgeApi.delete(id);
      if (res.data?.success) {
        setNotification('Knowledge entry deleted.');
        fetchKnowledge();
      }
    } catch (err) {
      alert(err.response?.data?.message || 'Failed to delete knowledge entry');
    } finally {
      setTimeout(() => setNotification(''), 3000);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight">Shop Knowledge Base</h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            The AI assistant answers customer questions using ONLY the information saved here.
          </p>
        </div>
        <button
          onClick={openAddModal}
          className="inline-flex items-center space-x-2 px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs transition shadow-md shadow-blue-500/20 shrink-0"
        >
          <Plus className="w-4 h-4" />
          <span>Add Knowledge Entry</span>
        </button>
      </div>

      {/* Success Notification Banner */}
      {notification && (
        <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-semibold flex items-center space-x-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          <span>{notification}</span>
        </div>
      )}

      {/* Filter & Search Bar */}
      <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm flex flex-col md:flex-row gap-3 items-center justify-between">
        <form onSubmit={handleSearchSubmit} className="relative w-full md:w-96">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
          <input
            type="text"
            placeholder="Search title, content, keywords..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 rounded-xl border border-slate-200 text-xs focus:ring-2 focus:ring-blue-500 focus:outline-none"
          />
        </form>

        <div className="flex items-center space-x-2 w-full md:w-auto">
          <Filter className="w-4 h-4 text-slate-400 shrink-0" />
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="px-3 py-2 rounded-xl border border-slate-200 text-xs font-medium text-slate-700 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All Categories</option>
            {categories.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
          {(search || selectedCategory) && (
            <button
              onClick={() => { setSearch(''); setSelectedCategory(''); }}
              className="text-xs text-blue-600 font-semibold hover:underline"
            >
              Reset
            </button>
          )}
        </div>
      </div>

      {/* Knowledge Entries List */}
      {loading ? (
        <div className="flex flex-col items-center justify-center py-16 space-y-2">
          <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
          <p className="text-xs text-slate-500">Loading knowledge entries...</p>
        </div>
      ) : entries.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-2xl border border-dashed border-slate-200 p-8 shadow-sm">
          <div className="w-12 h-12 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center mx-auto mb-3">
            <BookOpen className="w-6 h-6" />
          </div>
          <h3 className="text-base font-bold text-slate-800">Knowledge Base is Empty</h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto mt-1 mb-5">
            Add information about your opening hours, products, services, returns, and payment methods so your AI can assist customers.
          </p>
          <button
            onClick={openAddModal}
            className="inline-flex items-center space-x-1.5 px-4 py-2 rounded-xl bg-blue-600 text-white font-bold text-xs hover:bg-blue-700 transition"
          >
            <Plus className="w-4 h-4" />
            <span>Create First Entry</span>
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {entries.map((entry) => (
            <div key={entry.id} className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm hover:shadow-md transition flex flex-col justify-between">
              <div>
                <div className="flex items-start justify-between gap-2 mb-2">
                  <h3 className="font-bold text-slate-900 text-sm">{entry.title}</h3>
                  <div className="flex items-center space-x-1 shrink-0">
                    <button
                      onClick={() => openEditModal(entry)}
                      className="p-1.5 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition"
                      title="Edit knowledge"
                    >
                      <Edit3 className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => handleDelete(entry.id, entry.title)}
                      className="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition"
                      title="Delete knowledge"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-1.5 mb-3">
                  <span className="px-2 py-0.5 rounded-md bg-blue-50 text-blue-700 text-[10px] font-bold">
                    {entry.category}
                  </span>

                  {/* Source Badges */}
                  {entry.source_type === 'pending_answered' && (
                    <span className="px-2 py-0.5 rounded-md bg-emerald-50 text-emerald-700 border border-emerald-200 text-[10px] font-bold flex items-center space-x-1">
                      <Sparkles className="w-3 h-3 text-emerald-600" />
                      <span>Learned from Question</span>
                    </span>
                  )}
                  {entry.source_type === 'feedback_correction' && (
                    <span className="px-2 py-0.5 rounded-md bg-purple-50 text-purple-700 border border-purple-200 text-[10px] font-bold flex items-center space-x-1">
                      <Sparkles className="w-3 h-3 text-purple-600" />
                      <span>Learned from Correction</span>
                    </span>
                  )}
                </div>

                <p className="text-xs text-slate-600 whitespace-pre-wrap leading-relaxed">
                  {entry.content}
                </p>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-[10px] text-slate-400 font-mono">
                <span>ID: #{entry.id}</span>
                <span>Updated: {new Date(entry.updated_at || entry.created_at).toLocaleDateString()}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add / Edit Modal */}
      {modalOpen && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-base font-bold text-slate-900">
                {isEditing ? 'Edit Knowledge Entry' : 'Add New Knowledge Entry'}
              </h3>
              <button
                onClick={() => setModalOpen(false)}
                className="p-1 text-slate-400 hover:text-slate-600 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {formError && (
              <div className="mb-4 p-3 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs flex items-center space-x-2">
                <AlertCircle className="w-4 h-4 shrink-0 text-red-500" />
                <span>{formError}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-[11px] font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Title / Subject
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Shop Timings, Return Policy, Samsung Brands"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl border border-slate-300 text-xs focus:ring-2 focus:ring-blue-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-[11px] font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Category
                </label>
                <input
                  type="text"
                  placeholder="e.g. Timings, Products, Policy, Delivery"
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl border border-slate-300 text-xs focus:ring-2 focus:ring-blue-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-[11px] font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Content / Details
                </label>
                <textarea
                  rows={5}
                  required
                  placeholder="Provide precise details for your AI. For example: Our shop opens at 9 AM and closes at 9 PM Monday to Saturday. Sunday is a holiday."
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl border border-slate-300 text-xs focus:ring-2 focus:ring-blue-500 focus:outline-none leading-relaxed"
                />
              </div>

              <div className="flex items-center justify-end space-x-3 pt-2">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="px-4 py-2 rounded-xl border border-slate-200 text-slate-600 text-xs font-semibold hover:bg-slate-50 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-5 py-2 rounded-xl bg-blue-600 text-white font-bold text-xs hover:bg-blue-700 transition shadow-sm disabled:opacity-50 flex items-center space-x-1.5"
                >
                  {submitting ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>Saving...</span>
                    </>
                  ) : (
                    <span>{isEditing ? 'Save Changes' : 'Create Entry'}</span>
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

export default KnowledgeBasePage;

