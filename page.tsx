"use client";

import { FormEvent, useEffect, useState } from "react";

type Result = { title?: string; snippet?: string; content?: string; source?: string; document_id?: string; score?: number };
type SearchResponse = { ai_synthesis?: { summary?: string } | string; summary?: string; results?: Result[]; detail?: string; message?: string };

declare global {
  interface Window {
    google?: { accounts?: { id?: {
      initialize: (config: { client_id: string; callback: (response: { credential?: string }) => void }) => void;
      renderButton: (parent: HTMLElement, options: Record<string, string | number | boolean>) => void;
    } } };
  }
}

export default function Home() {
  const [query, setQuery] = useState("");
  const [token, setToken] = useState("");
  const [email, setEmail] = useState("");
  const [results, setResults] = useState<Result[]>([]);
  const [summary, setSummary] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [authLoading, setAuthLoading] = useState(false);
  const backendUrl = (process.env.NEXT_PUBLIC_BACKEND_URL || "").replace(/\\/+$/, "");
  const googleClientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || "";

  useEffect(() => {
    if (!googleClientId) return;
    const scriptId = "google-identity-services";
    const renderGoogleButton = () => {
      const container = document.getElementById("google-signin-button");
      if (!container || !window.google?.accounts?.id) return;
      container.innerHTML = "";
      window.google.accounts.id.initialize({
        client_id: googleClientId,
        callback: async (response) => {
          if (!response.credential) { setError("Google did not return an ID token. Check Google OAuth settings."); return; }
          setAuthLoading(true); setError("");
          try {
            if (!backendUrl) throw new Error("Set NEXT_PUBLIC_BACKEND_URL in Vercel.");
            const res = await fetch(`${backendUrl}/api/v1/auth/google`, {
              method: "POST", headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ id_token: response.credential })
            });
            const data = await res.json().catch(() => ({}));
            if (!res.ok) throw new Error(data.detail || data.message || `Google login failed (${res.status}).`);
            const appToken = data.access_token || data.token;
            if (!appToken) throw new Error("Backend response did not include access_token or token. Check its auth response schema.");
            setToken(appToken); setEmail(data.email || data.user?.email || "Signed in with Google");
          } catch (e) { setError(e instanceof Error ? e.message : "Google sign-in failed."); }
          finally { setAuthLoading(false); }
        }
      });
      window.google.accounts.id.renderButton(container, { theme: "filled_black", size: "large", shape: "rectangular", text: "signin_with", width: 300 });
    };
    const existing = document.getElementById(scriptId);
    if (existing) { renderGoogleButton(); return; }
    const script = document.createElement("script");
    script.id = scriptId; script.src = "https://accounts.google.com/gsi/client"; script.async = true; script.defer = true;
    script.onload = renderGoogleButton; document.head.appendChild(script);
  }, [backendUrl, googleClientId]);

  async function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!query.trim()) { setError("Enter a question or search phrase first."); return; }
    if (!backendUrl) { setError("Set NEXT_PUBLIC_BACKEND_URL in Vercel."); return; }
    if (!token) { setError("Sign in with Google before searching."); return; }
    setLoading(true); setError(""); setSummary(""); setResults([]);
    try {
      const res = await fetch(`${backendUrl}/api/v1/search`, {
        method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ query: query.trim(), page: 1, page_size: 10 })
      });
      const data: SearchResponse = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || data.message || `Search failed (${res.status}).`);
      const synth = data.ai_synthesis;
      setSummary((typeof synth === "string" ? synth : synth?.summary) || data.summary || "");
      setResults(Array.isArray(data.results) ? data.results : []);
      if (!Array.isArray(data.results) && !data.summary && !data.ai_synthesis) setError("Backend responded with a different result format. Check /api/v1/search schema.");
    } catch (e) { setError(e instanceof Error ? e.message : "Search failed. Check backend URL, CORS and API schema."); }
    finally { setLoading(false); }
  }

  return <main className="shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-icon">✦</div><div><div className="brand-title">ENTERPRISE INTELLIGENCE</div><div className="brand-sub">Knowledge Graph Platform</div></div></div>
      <div><div className="nav-label">WORKSPACE</div><div className="nav-item active">⌕ &nbsp; Knowledge Search</div><div className="nav-item">◎ &nbsp; Knowledge Graph</div><div className="nav-item">▤ &nbsp; Documents &amp; Evidence</div><div className="nav-item">⌘ &nbsp; Security &amp; Audit</div></div>
      <div className="sidebar-bottom"><div className="status"><span className="status-dot"/> Frontend ready<br/><span>Backend connectivity is verified when you sign in or search.</span></div></div>
    </aside>
    <section className="main">
      <header className="topbar"><div><div className="eyebrow">ENTERPRISE KNOWLEDGE WORKSPACE</div><h1 className="top-title">Enterprise Intelligence Platform</h1><div className="subheading">Search company knowledge with evidence-backed results.</div></div><div className="avatar">{email ? "✓" : "EI"}</div></header>
      {!token ? <section className="login-shell">
        <div className="login-left"><div className="brand"><div className="brand-icon">✦</div><div><div className="brand-title">ENTERPRISE INTELLIGENCE</div><div className="brand-sub">Secure context retrieval</div></div></div>
          <div className="login-promo"><div className="eyebrow">PRIVATE KNOWLEDGE. CLEAR ANSWERS.</div><h1>Turn enterprise knowledge into <span className="gradient-text">decisions.</span></h1><p>Search connected company knowledge and explore relevant documents through one focused workspace.</p><div className="feature-list"><span>✓ Search company information</span><span>✓ Review source evidence</span><span>✓ Connect to your existing backend</span></div></div><div className="footer">Enterprise Knowledge Graph &amp; FastMCP</div>
        </div>
        <div className="login-right"><div className="login-card"><h2>Welcome back</h2><p>Sign in with your Google account to access the knowledge workspace.</p>
          {!googleClientId ? <div className="alert">Google sign-in needs NEXT_PUBLIC_GOOGLE_CLIENT_ID in Vercel.</div> : <div id="google-signin-button"/>}
          {authLoading && <p>Signing in securely…</p>}<p className="fine-print">Access is subject to your organization's authentication and authorization rules.</p></div></div>
      </section> : <>
        <section className="hero"><div className="hero-top">✦ SECURE ENTERPRISE SEARCH <span className="pill">Google authenticated</span></div><h2>What would you like to know?</h2><p>Ask a question about your organization's knowledge. Results are retrieved from your configured backend.</p>
          <form className="search-form" onSubmit={handleSearch}><div className="search-wrap"><span>⌕</span><input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search policies, contracts, vendors, or documents…" aria-label="Search query"/></div><button className="primary" type="submit" disabled={loading}>{loading ? "Searching…" : "Search knowledge →"}</button></form>
        </section>
        <div className="section-head"><h3>Answer &amp; evidence</h3><span>{results.length} results</span></div>
        {summary && <article className="content-card"><div className="result-title">AI synthesis</div><div className="result-snippet">{summary}</div></article>}
        {results.map((item, i) => <article className="content-card" key={`${item.document_id || item.title || "result"}-${i}`}><div className="result-title">{item.title || item.source || `Search result ${i+1}`}</div><div className="result-snippet">{item.snippet || item.content || "No excerpt was provided by the backend."}</div><div className="result-meta">{item.source && <span className="tag">{item.source}</span>}{typeof item.score === "number" && <span className="tag">Score: {item.score.toFixed(3)}</span>}</div></article>)}
        {!summary && results.length === 0 && !loading && <div className="empty">Your search answers and supporting documents will appear here.</div>}
        <button className="primary" type="button" onClick={() => {setToken("");setEmail("");setResults([]);setSummary("");}}>Sign out</button>
      </>}
      {error && <div className="alert" role="alert">{error}</div>}
      {!backendUrl && <div className="alert">Backend URL is not configured. Add NEXT_PUBLIC_BACKEND_URL in Vercel before testing.</div>}
    </section>
  </main>;
}
