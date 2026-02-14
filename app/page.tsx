'use client';

import { useState } from 'react';

// Define the shape of our article data
interface ArticleData {
  title: string;
  content: string;
  excerpt?: string;
  byline?: string;
  siteName?: string;
}

export default function ReaderPage() {
  const [url, setUrl] = useState('');
  const [article, setArticle] = useState<ArticleData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleExtract = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url) return;

    setLoading(true);
    setError('');
    setArticle(null);

    try {
      // Call our Edge API
      const res = await fetch(`/api/extract?url=${encodeURIComponent(url)}`);
      
      if (!res.ok) {
        throw new Error('Failed to fetch the page. It might be blocked or invalid.');
      }

      const data = await res.json();

      if (data.error) {
        throw new Error(data.error);
      }

      setArticle(data);
    } catch (err: any) {
      setError(err.message || 'Something went wrong. Please try a different URL.');
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setUrl('');
    setArticle(null);
    setError('');
  };

  return (
    <div className="min-h-screen bg-[#f9f9f9] text-gray-900 font-sans selection:bg-blue-100">
      {/* --- Navbar --- */}
      <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-gray-200">
        <div className="max-w-4xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
            </svg>
            <span className="font-bold text-xl tracking-tight">JustRead</span>
          </div>
          {article && (
            <button 
              onClick={handleClear}
              className="text-sm font-medium text-gray-500 hover:text-red-600 transition-colors"
            >
              Clear Article
            </button>
          )}
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-12">
        
        {/* --- Search Section (Hidden when reading) --- */}
        {!article && (
          <div className="flex flex-col items-center justify-center min-h-[60vh] text-center space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
            <div className="space-y-4">
              <h1 className="text-4xl md:text-5xl font-extrabold text-gray-900 tracking-tight">
                Read the web, <span className="text-blue-600">distraction free.</span>
              </h1>
              <p className="text-lg text-gray-600 max-w-lg mx-auto">
                Paste any article URL below to strip away ads, popups, and clutter.
              </p>
            </div>

            <form onSubmit={handleExtract} className="w-full max-w-xl relative">
              <div className="relative flex items-center">
                <input
                  type="url"
                  placeholder="https://..."
                  className="w-full pl-6 pr-32 py-4 text-lg bg-white border border-gray-200 rounded-full shadow-lg focus:ring-4 focus:ring-blue-100 focus:border-blue-500 outline-none transition-all"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  required
                />
                <button
                  type="submit"
                  disabled={loading}
                  className="absolute right-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-full px-6 py-2.5 transition-all disabled:opacity-70 disabled:cursor-not-allowed"
                >
                  {loading ? (
                    <span className="flex items-center gap-2">
                      <svg className="animate-spin h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Parsing
                    </span>
                  ) : (
                    'Read Now'
                  )}
                </button>
              </div>
              {error && (
                <div className="mt-4 p-4 bg-red-50 text-red-600 text-sm rounded-lg border border-red-100 flex items-center gap-2">
                  <svg className="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                  {error}
                </div>
              )}
            </form>
          </div>
        )}

        {/* --- Loading Skeleton --- */}
        {loading && !article && (
          <div className="space-y-4 max-w-2xl mx-auto mt-12 animate-pulse">
            <div className="h-8 bg-gray-200 rounded w-3/4"></div>
            <div className="h-4 bg-gray-200 rounded w-1/4 mb-12"></div>
            <div className="space-y-3">
              <div className="h-4 bg-gray-200 rounded"></div>
              <div className="h-4 bg-gray-200 rounded"></div>
              <div className="h-4 bg-gray-200 rounded w-5/6"></div>
            </div>
          </div>
        )}

        {/* --- Article View --- */}
        {article && (
          <article className="animate-in fade-in zoom-in-95 duration-500 bg-white p-8 md:p-14 rounded-2xl shadow-xl border border-gray-100/50">
            <header className="mb-10 text-center">
              <h1 className="text-3xl md:text-5xl font-serif font-bold text-gray-900 mb-6 leading-tight">
                {article.title}
              </h1>
              
              <div className="flex flex-wrap items-center justify-center gap-4 text-sm text-gray-500 font-medium uppercase tracking-wider">
                {article.siteName && (
                  <span className="flex items-center gap-1">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" /></svg>
                    {article.siteName}
                  </span>
                )}
                {article.byline && (
                  <span className="flex items-center gap-1">
                     <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" /></svg>
                    {article.byline}
                  </span>
                )}
              </div>
            </header>

            {/* The Main Content */}
            <div 
              className="prose prose-lg prose-blue prose-headings:font-serif prose-headings:font-bold prose-p:text-gray-700 prose-p:leading-relaxed prose-a:text-blue-600 prose-img:rounded-xl max-w-none"
              dangerouslySetInnerHTML={{ __html: article.content }} 
            />
          </article>
        )}

      </main>
    </div>
  );
}