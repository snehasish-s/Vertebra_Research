import { useCallback, useEffect, useRef, useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  ArrowUp,
  BookOpen,
  Check,
  FileText,
  LockKeyhole,
  Plus,
  RefreshCw,
  Search,
  Trash2,
  Upload,
  X,
} from "lucide-react";
import { Link } from "react-router-dom";
import Brand from "../components/Brand";
import CitationViewer from "../components/CitationViewer";
import { askQuestion, request, setAccessToken, uploadDocument } from "../api";

const suggestions = [
  "What is the project’s research question?",
  "What are the main findings across these documents?",
  "What limitations should I keep in mind?",
];

export default function Dashboard() {
  const [config, setConfig] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [asking, setAsking] = useState(false);
  const [question, setQuestion] = useState("");
  const [history, setHistory] = useState([]);
  const [citation, setCitation] = useState(null);
  const [locked, setLocked] = useState(false);
  const [passphrase, setPassphrase] = useState("");
  const [deleting, setDeleting] = useState(null);
  const [notice, setNotice] = useState("");
  const input = useRef(null);
  const questionInput = useRef(null);
  const answersEnd = useRef(null);
  const readyCount = documents.filter(
    (document) => document.status === "ready",
  ).length;

  const refresh = useCallback(async () => {
    try {
      setDocuments(await request("/api/documents"));
    } catch (failure) {
      setError(failure.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    request("/api/config")
      .then((value) => {
        setConfig(value);
        setLocked(value.access_required);
        if (!value.access_required) refresh();
        else setLoading(false);
      })
      .catch((failure) => {
        setError(failure.message);
        setLoading(false);
      });
  }, [refresh]);

  useEffect(() => {
    if (
      !uploading &&
      !documents.some((item) =>
        ["extracting", "embedding"].includes(item.status),
      )
    )
      return;
    const timer = setInterval(refresh, 3000);
    return () => clearInterval(timer);
  }, [uploading, documents, refresh]);

  useEffect(() => {
    answersEnd.current?.scrollIntoView({ block: "nearest" });
  }, [history, asking]);

  async function unlock(event) {
    event.preventDefault();
    setAccessToken(passphrase);
    setError("");
    try {
      setDocuments(await request("/api/documents"));
      setLocked(false);
      setPassphrase("");
    } catch (failure) {
      setError(failure.message);
      setAccessToken("");
    }
  }

  async function handleUpload(file) {
    if (!file || uploading) return;
    setError("");
    setNotice("");
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setError("Please choose a PDF file.");
      return;
    }
    if (file.size > (config?.max_file_mb || 10) * 1024 * 1024) {
      setError(
        `Please choose a PDF smaller than ${config?.max_file_mb || 10} MB.`,
      );
      return;
    }
    setUploading(true);
    try {
      const result = await uploadDocument(file);
      setNotice(`${result.title} is ready to research.`);
    } catch (failure) {
      setError(failure.message);
    } finally {
      setUploading(false);
      if (input.current) input.current.value = "";
      await refresh();
    }
  }

  async function removeDocument(document) {
    if (
      !window.confirm(
        `Delete “${document.title}” and its searchable passages? This cannot be undone.`,
      )
    )
      return;
    setDeleting(document.id);
    setError("");
    try {
      await request(`/api/documents/${document.id}`, { method: "DELETE" });
      // Clear old answers: their evidence may no longer exist after a deletion.
      setHistory([]);
      setCitation(null);
      await refresh();
      setNotice("Document and its passages deleted.");
    } catch (failure) {
      setError(failure.message);
      await refresh();
    } finally {
      setDeleting(null);
    }
  }

  async function submitQuestion(event) {
    event.preventDefault();
    const value = question.trim();
    if (asking || value.length < 3 || !readyCount) return;
    setAsking(true);
    setError("");
    try {
      const result = await askQuestion(value);
      setHistory((previous) => [...previous, { question: value, result }]);
      setQuestion("");
    } catch (failure) {
      setError(failure.message);
    } finally {
      setAsking(false);
    }
  }

  return (
    <div className="workspace">
      <header className="workspace-header">
        <Brand />
        <div className="workspace-label">
          <span className="status-dot" /> RESEARCH WORKSPACE
        </div>
        <Link className="text-link" to="/">
          <ArrowLeft size={15} /> About Vertebra
        </Link>
      </header>
      {config?.mode === "local" && (
        <div className="mode-banner">
          LOCAL DEMONSTRATION{" "}
          <span>
            Uses word matching and source excerpts. Connect Supabase + OpenAI
            for semantic search and AI answers.
          </span>
        </div>
      )}
      {config?.mode === "ai" && (
        <div className="mode-banner ai-active">
          AI ASSISTANT ACTIVE{" "}
          <span>
            Connected to {config.ai_model || "NVIDIA / OpenAI"}. Generating grounded research answers with page-level citations.
          </span>
        </div>
      )}
      {error && (
        <div className="alert" role="alert">
          <span>{error}</span>
          <button
            onClick={() => setError("")}
            className="icon-button"
            aria-label="Dismiss error"
          >
            <X size={17} />
          </button>
        </div>
      )}
      {locked ? (
        <main className="access-panel">
          <LockKeyhole size={32} />
          <h1>A space for your research.</h1>
          <p>This shared demo library requires an access passphrase.</p>
          <form onSubmit={unlock}>
            <label htmlFor="passphrase">Demo passphrase</label>
            <input
              id="passphrase"
              type="password"
              autoComplete="off"
              value={passphrase}
              onChange={(event) => setPassphrase(event.target.value)}
              required
            />
            <button className="button primary">
              Open library <ArrowRight size={16} />
            </button>
          </form>
          <small>
            Use the demo passphrase from the host. Never enter an OpenAI or
            Supabase key here.
          </small>
        </main>
      ) : (
        <main className="workspace-grid">
          <aside className="library">
            <div className="library-heading">
              <div>
                <div className="eyebrow">YOUR FOUNDATION</div>
                <h2>
                  Library{" "}
                  <span>{documents.length.toString().padStart(2, "0")}</span>
                </h2>
              </div>
              <button
                className="icon-button"
                onClick={refresh}
                aria-label="Refresh documents"
              >
                <RefreshCw size={16} />
              </button>
            </div>
            <input
              ref={input}
              type="file"
              accept="application/pdf,.pdf"
              className="visually-hidden"
              id="pdf-upload"
              onChange={(event) => handleUpload(event.target.files[0])}
              disabled={uploading || !config?.uploads_enabled}
            />
            <button
              className={`upload-zone ${uploading ? "processing" : ""}`}
              onClick={() => input.current.click()}
              disabled={uploading || !config?.uploads_enabled}
              onDragOver={(event) => event.preventDefault()}
              onDrop={(event) => {
                event.preventDefault();
                if (config?.uploads_enabled)
                  handleUpload(event.dataTransfer.files[0]);
              }}
            >
              <span className="upload-icon">
                <Upload size={20} />
              </span>
              <strong>
                {uploading
                  ? "Processing your document…"
                  : config?.uploads_enabled
                    ? "Add your documents"
                    : "Uploads are disabled"}
              </strong>
              <span>
                {uploading
                  ? "Extracting pages and connecting passages"
                  : "Choose a PDF or drop it here"}
              </span>
              <small>
                PDF · Up to {config?.max_file_mb || 10} MB ·{" "}
                {config?.max_pages || 150} pages
              </small>
            </button>
            <div className="library-list" aria-live="polite">
              {loading ? (
                <p className="muted">Loading your library…</p>
              ) : documents.length === 0 ? (
                <div className="library-empty">
                  <FileText size={25} />
                  <p>A home for your sources.</p>
                  <small>Your uploaded documents will appear here.</small>
                </div>
              ) : (
                documents.map((document) => (
                  <article className="document-card" key={document.id}>
                    <FileText size={19} />
                    <div>
                      <h3 title={document.title}>{document.title}</h3>
                      <span className={`document-status ${document.status}`}>
                        {document.status === "ready" ? (
                          <>
                            <Check size={11} /> {document.page_count} pages ·
                            Ready
                          </>
                        ) : document.status === "error" ? (
                          "Needs attention"
                        ) : document.status === "deleting" ? (
                          "Deletion incomplete — retry"
                        ) : (
                          `${document.status}…`
                        )}
                      </span>
                      {document.error && (
                        <p className="document-error">{document.error}</p>
                      )}
                    </div>
                    <button
                      disabled={
                        !config?.deletes_enabled ||
                        uploading ||
                        Boolean(deleting)
                      }
                      className="icon-button"
                      aria-label={`Delete ${document.title}`}
                      onClick={() => removeDocument(document)}
                    >
                      <Trash2 size={15} />
                    </button>
                  </article>
                ))
              )}
            </div>
            <div className="library-footnote">
              <LockKeyhole size={15} />
              <p>
                Files are served through the backend.
                <br />
                This demo uses a shared library. Upload only material you are
                permitted to share.
              </p>
            </div>
          </aside>
          <section className="research-pane" aria-label="Research conversation">
            <div className="research-topline">
              <span>
                <BookOpen size={15} /> Research desk
              </span>
              <span>
                {readyCount} {readyCount === 1 ? "source" : "sources"} connected
              </span>
            </div>
            <div className="conversation">
              {history.length === 0 ? (
                <div className="research-empty">
                  <div className="empty-symbol">
                    <Search size={30} />
                    <span>+</span>
                  </div>
                  <div className="eyebrow">MAKE ROOM FOR A NEW CONNECTION</div>
                  <h1>
                    What will you
                    <br />
                    <em>discover today?</em>
                  </h1>
                  <p>
                    {readyCount
                      ? "Your sources are ready. Ask a question and follow the evidence."
                      : "Add a few PDFs. Ask a thoughtful question.\nLet your documents help you find the answer."}
                  </p>
                  <div className="suggestions">
                    {suggestions.map((value) => (
                      <button
                        key={value}
                        onClick={() => {
                          setQuestion(value);
                          questionInput.current.focus();
                        }}
                      >
                        <span>{value}</span>
                        <ArrowRight size={16} />
                      </button>
                    ))}
                  </div>
                  <span className="empty-hint">
                    <Plus size={12} /> Try the three small PDFs in
                    sample_documents/
                  </span>
                </div>
              ) : (
                history.map(({ question: asked, result }, index) => (
                  <article key={index} className="answer-turn">
                    <div className="asked-question">
                      <span className="eyebrow">YOUR QUESTION</span>
                      <h2>{asked}</h2>
                    </div>
                    <div className="answer-label">
                      <span className="status-dot" />{" "}
                      {result.abstained
                        ? "EVIDENCE CHECK"
                        : "FROM YOUR SOURCES"}
                    </div>
                    {result.abstained ? (
                      <p>{result.answer}</p>
                    ) : (
                      result.claims.map((claim, claimIndex) => (
                        <p className="answer-claim" key={claimIndex}>
                          {claim.text}{" "}
                          <span className="inline-citations">
                            {claim.source_ids.map((id) => {
                              const source = result.citations.find(
                                (item) => item.id === id,
                              );
                              return (
                                source && (
                                  <button
                                    key={id}
                                    onClick={() => setCitation(source)}
                                    aria-label={`Open ${source.title}, page ${source.page_number}`}
                                  >
                                    {result.citations.indexOf(source) + 1}
                                  </button>
                                )
                              );
                            })}
                          </span>
                        </p>
                      ))
                    )}
                    {result.citations.length > 0 && (
                      <div className="source-cards">
                        {result.citations.map((source, sourceIndex) => (
                          <button
                            key={source.id}
                            onClick={() => setCitation(source)}
                          >
                            <span className="source-number">
                              {sourceIndex + 1}
                            </span>
                            <span>
                              <strong>{source.title}</strong>
                              <small>
                                Page {source.page_number} · View source
                              </small>
                            </span>
                            <ArrowRight size={14} />
                          </button>
                        ))}
                      </div>
                    )}
                    <div className="answer-meta">
                      {result.mode === "local"
                        ? "Offline source excerpts"
                        : "AI answer · verify against sources"}{" "}
                      · {(result.latency_ms / 1000).toFixed(2)}s · Est. $
                      {result.estimated_cost_usd.toFixed(6)}
                    </div>
                  </article>
                ))
              )}
              {asking && (
                <p className="thinking" role="status">
                  <span className="status-dot" /> Finding connections in your
                  sources…
                </p>
              )}
              <div ref={answersEnd} />
            </div>
            <div className="composer-area">
              <form className="composer" onSubmit={submitQuestion}>
                <label className="visually-hidden" htmlFor="question">
                  Ask across your documents
                </label>
                <textarea
                  id="question"
                  ref={questionInput}
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" && !event.shiftKey) {
                      event.preventDefault();
                      submitQuestion(event);
                    }
                  }}
                  maxLength={1500}
                  rows={2}
                  placeholder={
                    readyCount
                      ? "Ask across your documents…"
                      : "Add a document to start asking questions…"
                  }
                />
                <button
                  className="send-button"
                  type="submit"
                  disabled={asking || !readyCount || question.trim().length < 3}
                  aria-label="Ask question"
                >
                  <ArrowUp size={20} />
                </button>
              </form>
              <div className="composer-note">
                <span>
                  Grounded in your documents. Always check the sources.
                </span>
                <span>{question.length}/1500</span>
              </div>
              {notice && (
                <p className="notice" role="status">
                  {notice}
                </p>
              )}
            </div>
          </section>
        </main>
      )}
      {citation && (
        <CitationViewer
          key={citation.id}
          citation={citation}
          onClose={() => setCitation(null)}
        />
      )}
    </div>
  );
}
