import { useEffect, useRef, useState } from "react";
import { X, FileText } from "lucide-react";
import { request } from "../api";

export default function CitationViewer({ citation, onClose }) {
  const dialog = useRef(null);
  const canvas = useRef(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    dialog.current.showModal();
    let cancelled = false;
    let loadingTask;
    let renderTask;
    async function renderPage() {
      try {
        const [pdfjs, data] = await Promise.all([
          import("pdfjs-dist"),
          request(`/api/documents/${citation.document_id}/pdf`, { pdf: true }),
        ]);
        if (cancelled) return;
        pdfjs.GlobalWorkerOptions.workerSrc = new URL(
          "pdfjs-dist/build/pdf.worker.min.mjs",
          import.meta.url,
        ).toString();
        loadingTask = pdfjs.getDocument({ data, isEvalSupported: false });
        const pdf = await loadingTask.promise;
        const page = await pdf.getPage(citation.page_number);
        if (cancelled) return;
        const base = page.getViewport({ scale: 1 });
        const ratio = Math.min(window.devicePixelRatio || 1, 2);
        const width = Math.min(720, canvas.current.parentElement.clientWidth);
        const viewport = page.getViewport({
          scale: (width / base.width) * ratio,
        });
        canvas.current.width = viewport.width;
        canvas.current.height = viewport.height;
        canvas.current.style.width = "100%";
        renderTask = page.render({
          canvasContext: canvas.current.getContext("2d"),
          viewport,
        });
        await renderTask.promise;
        if (!cancelled) setLoading(false);
      } catch (failure) {
        if (!cancelled) {
          setError(failure.message || "The PDF page could not be opened.");
          setLoading(false);
        }
      }
    }
    renderPage();
    return () => {
      cancelled = true;
      renderTask?.cancel();
      loadingTask?.destroy();
    };
  }, [citation]);

  return (
    <dialog
      ref={dialog}
      className="citation-dialog"
      onCancel={onClose}
      aria-labelledby="citation-title"
    >
      <div className="dialog-header">
        <div>
          <div className="eyebrow">FOLLOW THE EVIDENCE</div>
          <h2 id="citation-title">
            <FileText size={19} /> {citation.title}
          </h2>
          <span>Physical PDF page {citation.page_number}</span>
        </div>
        <button
          className="icon-button"
          onClick={onClose}
          aria-label="Close source"
        >
          <X size={22} />
        </button>
      </div>
      <div className="source-excerpt">
        <span className="eyebrow">CITED PASSAGE</span>
        <blockquote>{citation.excerpt}</blockquote>
      </div>
      <div className="pdf-page">
        {loading && <p role="status">Opening page {citation.page_number}…</p>}
        {error && <p role="alert">{error}</p>}
        <canvas
          ref={canvas}
          role="img"
          aria-label={`${citation.title}, page ${citation.page_number}. The cited text appears above.`}
        />
      </div>
    </dialog>
  );
}
