import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { shopApi } from '../../services/api';
import { 
  Store, 
  Globe, 
  ExternalLink, 
  Copy, 
  Check, 
  CheckCircle2, 
  AlertCircle, 
  Loader2, 
  Save, 
  User,
  ShieldCheck
} from 'lucide-react';

const ShopSettingsPage = () => {
  const { shop, user, refreshShopProfile } = useAuth();

  const [shopName, setShopName] = useState(shop?.shop_name || '');
  const [slug, setSlug] = useState(shop?.slug || '');
  const [description, setDescription] = useState(shop?.description || '');
  const [logoUrl, setLogoUrl] = useState(shop?.logo_url || '');

  const [loading, setLoading] = useState(false);
  const [notification, setNotification] = useState('');
  const [error, setError] = useState('');
  const [copied, setCopied] = useState(false);

  const publicUrl = `${window.location.origin}/s/${slug || shop?.slug || ''}`;

  const handleCopyLink = () => {
    navigator.clipboard.writeText(publicUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!shopName.trim()) {
      setError('Shop name is required.');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const res = await shopApi.updateProfile({
        shop_name: shopName.trim(),
        slug: slug.trim(),
        description: description.trim(),
        logo_url: logoUrl.trim()
      });
      if (res.data?.success) {
        setNotification('Shop settings updated successfully!');
        await refreshShopProfile();
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to update shop settings');
    } finally {
      setLoading(false);
      setTimeout(() => setNotification(''), 3000);
    }
  };

  return (
    <div className="max-w-4xl space-y-6">
      <div>
        <h1 className="text-2xl font-black text-slate-900 tracking-tight">Shop Settings</h1>
        <p className="text-xs sm:text-sm text-slate-500 mt-1">
          Manage your shop profile, URL slug, and public chatbot configuration.
        </p>
      </div>

      {notification && (
        <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-semibold flex items-center space-x-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          <span>{notification}</span>
        </div>
      )}

      {error && (
        <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 text-red-500" />
          <span>{error}</span>
        </div>
      )}

      {/* Public Chatbot URL Card */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
        <div className="flex items-center space-x-2">
          <Globe className="w-5 h-5 text-blue-600" />
          <h2 className="text-base font-bold text-slate-900">Public Chatbot Link</h2>
        </div>
        <p className="text-xs text-slate-600">
          This is the permanent unique web address where customers access your AI assistant:
        </p>
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
          <div className="flex-1 bg-slate-50 border border-slate-200 px-3.5 py-2.5 rounded-xl font-mono text-xs text-slate-800 select-all">
            {publicUrl}
          </div>
          <button
            type="button"
            onClick={handleCopyLink}
            className="inline-flex items-center justify-center space-x-1.5 px-4 py-2.5 rounded-xl bg-slate-900 text-white text-xs font-bold hover:bg-slate-800 transition"
          >
            {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
            <span>{copied ? 'Copied!' : 'Copy Link'}</span>
          </button>
          <a
            href={`/s/${slug || shop?.slug}`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center justify-center space-x-1.5 px-4 py-2.5 rounded-xl bg-blue-600 text-white text-xs font-bold hover:bg-blue-700 transition"
          >
            <ExternalLink className="w-4 h-4" />
            <span>Open Chatbot</span>
          </a>
        </div>
      </div>

      {/* Profile Form */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
              Shop Name
            </label>
            <input
              type="text"
              required
              value={shopName}
              onChange={(e) => setShopName(e.target.value)}
              className="w-full px-4 py-2.5 rounded-xl border border-slate-300 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
              URL Slug
            </label>
            <input
              type="text"
              required
              value={slug}
              onChange={(e) => setSlug(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ''))}
              className="w-full px-4 py-2.5 rounded-xl border border-slate-300 text-sm font-mono focus:ring-2 focus:ring-blue-500 focus:outline-none"
            />
            <span className="block text-[11px] text-slate-400 mt-1">
              Modifying the slug will change your public chatbot URL.
            </span>
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
              Shop Description
            </label>
            <textarea
              rows={3}
              placeholder="A brief overview of your business..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-4 py-2.5 rounded-xl border border-slate-300 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
            />
          </div>

          <div className="pt-2">
            <button
              type="submit"
              disabled={loading}
              className="inline-flex items-center space-x-2 px-6 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs transition shadow-md shadow-blue-500/20 disabled:opacity-50"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Saving...</span>
                </>
              ) : (
                <>
                  <Save className="w-4 h-4" />
                  <span>Save Settings</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>

      {/* Owner Account Card */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-slate-100 text-slate-600 flex items-center justify-center">
            <User className="w-5 h-5" />
          </div>
          <div>
            <h4 className="text-sm font-bold text-slate-900">{user?.full_name}</h4>
            <p className="text-xs text-slate-500">{user?.email}</p>
          </div>
        </div>
        <div className="flex items-center space-x-1.5 text-xs text-emerald-600 font-semibold bg-emerald-50 px-3 py-1.5 rounded-xl border border-emerald-200">
          <ShieldCheck className="w-4 h-4" />
          <span>Tenant Owner Verified</span>
        </div>
      </div>
    </div>
  );
};

export default ShopSettingsPage;

