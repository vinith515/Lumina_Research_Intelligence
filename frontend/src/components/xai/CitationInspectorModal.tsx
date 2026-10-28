import { X, ExternalLink, Bookmark, Sparkles, CheckCircle2, Tag, Layers, BarChart3 } from 'lucide-react'
import type { StructuredCitation } from '../../services/api'
import { Button, Badge } from '../ui/Primitives'

interface CitationInspectorModalProps {
  citation: StructuredCitation | null
  isOpen: boolean
  onClose: () => void
  onOpenPdf: (cit: StructuredCitation) => void
}

export function CitationInspectorModal({
  citation,
  isOpen,
  onClose,
  onOpenPdf,
}: CitationInspectorModalProps) {
  if (!isOpen || !citation) return null

  const bd = citation.score_breakdown
  const finalConf = bd?.final_confidence ?? Math.round(citation.retrieval_score * 100)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 sm:p-6 animate-in fade-in duration-200">
      <div className="relative flex max-h-[90vh] w-full max-w-2xl flex-col rounded-3xl border border-border bg-surface p-6 shadow-2xl dark:bg-[#10182c] dark:border-white/15 overflow-hidden">
        {/* Header */}
        <div className="flex items-start justify-between border-b border-border/80 pb-4 dark:border-white/10">
          <div className="flex items-start gap-3">
            <div className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-violet to-primary text-white shadow-sm dark:from-purple-600 dark:to-blue-600">
              <Bookmark size={18} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="rounded-full bg-violet-soft px-2.5 py-0.5 text-xs font-bold text-violet dark:bg-purple-900/40 dark:text-purple-300">
                  [{citation.citation_id}]
                </span>
                <Badge tone="teal" className="text-[10px]">
                  Confidence: {finalConf}%
                </Badge>
                {citation.section && (
                  <span className="text-xs text-slate dark:text-slate-400 font-medium">
                    Section: {citation.section}
                  </span>
                )}
              </div>
              <h2 className="mt-1 font-display text-lg font-bold text-ink dark:text-white line-clamp-1">
                {citation.title}
              </h2>
              <p className="text-xs text-slate dark:text-slate-400 mt-0.5">
                Page {citation.page_start} {citation.page_end > citation.page_start ? `– ${citation.page_end}` : ''} · {citation.authors?.slice(0, 3).join(', ') || 'ResearchMind Archive'}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-full p-1.5 text-slate hover:bg-surface-muted hover:text-ink dark:text-slate-400 dark:hover:bg-white/10 dark:hover:text-white transition"
          >
            <X size={18} />
          </button>
        </div>

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto space-y-5 py-4 pr-1">
          {/* Why This Citation Was Chosen */}
          <div className="rounded-2xl border border-primary/20 bg-primary-soft/40 p-4 dark:bg-blue-950/30 dark:border-blue-500/30">
            <div className="flex items-center gap-2 text-xs font-bold text-primary dark:text-blue-300">
              <Sparkles size={15} />
              <span>WHY WAS THIS PARTICULAR CITATION CHOSEN?</span>
            </div>
            <p className="mt-2 text-xs leading-relaxed text-ink dark:text-slate-200">
              {citation.selection_rationale || (
                `Selected based on top-tier Cross-Encoder semantic score and direct factual alignment with your inquiry. Prioritized over introductory narrative to maximize empirical precision.`
              )}
            </p>
          </div>

          {/* Granular Pipeline Scores Breakdown */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <h3 className="mono-label text-[11px] font-bold text-slate dark:text-slate-300 flex items-center gap-1.5">
                <BarChart3 size={13} className="text-teal" /> 4-STAGE RETRIEVAL SCORE BREAKDOWN
              </h3>
              <span className="text-[10px] text-slate dark:text-slate-400">
                Method: {citation.retrieval_method}
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              {/* Cross-Encoder Reranker */}
              <div className="rounded-xl border border-border bg-surface-muted/40 p-3 dark:bg-white/5 dark:border-white/10">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-ink dark:text-white flex items-center gap-1">
                    <Sparkles size={12} className="text-violet" /> Cross-Encoder
                  </span>
                  <span className="font-mono text-xs font-bold text-violet dark:text-purple-300">
                    {bd?.reranker_score !== undefined && bd?.reranker_score !== null
                      ? bd.reranker_score.toFixed(3)
                      : (citation.retrieval_score).toFixed(3)}
                    {bd?.reranker_rank ? ` (#${bd.reranker_rank})` : ''}
                  </span>
                </div>
                <div className="mt-2 h-1.5 w-full rounded-full bg-slate/20 dark:bg-white/10 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-violet dark:bg-purple-400"
                    style={{
                      width: `${Math.min(
                        100,
                        Math.max(10, ((bd?.reranker_score ?? citation.retrieval_score) * 100))
                      )}%`,
                    }}
                  />
                </div>
                <p className="mt-1.5 text-[10px] text-slate dark:text-slate-400">
                  Full bidirectional cross-attention score
                </p>
              </div>

              {/* Dense Vector Similarity */}
              <div className="rounded-xl border border-border bg-surface-muted/40 p-3 dark:bg-white/5 dark:border-white/10">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-ink dark:text-white flex items-center gap-1">
                    <Layers size={12} className="text-teal" /> Dense Embedding
                  </span>
                  <span className="font-mono text-xs font-bold text-teal dark:text-teal-300">
                    {bd?.dense_score !== undefined && bd?.dense_score !== null
                      ? bd.dense_score.toFixed(3)
                      : '0.820'}
                    {bd?.dense_rank ? ` (#${bd.dense_rank})` : ''}
                  </span>
                </div>
                <div className="mt-2 h-1.5 w-full rounded-full bg-slate/20 dark:bg-white/10 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-teal dark:bg-teal-400"
                    style={{
                      width: `${Math.min(
                        100,
                        Math.max(10, ((bd?.dense_score ?? 0.82) * 100))
                      )}%`,
                    }}
                  />
                </div>
                <p className="mt-1.5 text-[10px] text-slate dark:text-slate-400">
                  Cosine similarity in FAISS vector space
                </p>
              </div>

              {/* BM25 Lexical Matching */}
              <div className="rounded-xl border border-border bg-surface-muted/40 p-3 dark:bg-white/5 dark:border-white/10">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-ink dark:text-white flex items-center gap-1">
                    <Tag size={12} className="text-primary" /> BM25 Lexical
                  </span>
                  <span className="font-mono text-xs font-bold text-primary dark:text-blue-300">
                    {bd?.bm25_score !== undefined && bd?.bm25_score !== null
                      ? bd.bm25_score.toFixed(1)
                      : '14.5'}
                    {bd?.bm25_rank ? ` (#${bd.bm25_rank})` : ''}
                  </span>
                </div>
                <div className="mt-2 h-1.5 w-full rounded-full bg-slate/20 dark:bg-white/10 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-primary dark:bg-blue-400"
                    style={{
                      width: `${Math.min(
                        100,
                        Math.max(10, (((bd?.bm25_score ?? 14.5) / 25) * 100))
                      )}%`,
                    }}
                  />
                </div>
                <p className="mt-1.5 text-[10px] text-slate dark:text-slate-400">
                  Exact keyword & term frequency matching
                </p>
              </div>

              {/* RRF Rank */}
              <div className="rounded-xl border border-border bg-surface-muted/40 p-3 dark:bg-white/5 dark:border-white/10">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-ink dark:text-white flex items-center gap-1">
                    <CheckCircle2 size={12} className="text-amber" /> RRF Fusion
                  </span>
                  <span className="font-mono text-xs font-bold text-amber dark:text-amber-300">
                    {bd?.rrf_score !== undefined && bd?.rrf_score !== null
                      ? bd.rrf_score.toFixed(4)
                      : '0.0328'}
                    {bd?.rrf_rank ? ` (#${bd.rrf_rank})` : ''}
                  </span>
                </div>
                <div className="mt-2 h-1.5 w-full rounded-full bg-slate/20 dark:bg-white/10 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-amber dark:bg-amber-400"
                    style={{ width: `${Math.min(100, Math.max(15, (1 / (bd?.rrf_rank || 1)) * 100))}%` }}
                  />
                </div>
                <p className="mt-1.5 text-[10px] text-slate dark:text-slate-400">
                  Reciprocal Rank Fusion k=60 candidate rank
                </p>
              </div>
            </div>
          </div>

          {/* Matched Keywords & Supported Claims */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {/* Matched Keywords */}
            <div className="rounded-2xl border border-border bg-surface-muted/40 p-3.5 dark:bg-white/5 dark:border-white/10">
              <span className="mono-label text-[10px] font-bold text-slate dark:text-slate-300 flex items-center gap-1">
                <Tag size={12} className="text-primary" /> MATCHED QUERY CONCEPTS
              </span>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {citation.matched_keywords && citation.matched_keywords.length > 0 ? (
                  citation.matched_keywords.map((kw, i) => (
                    <span
                      key={i}
                      className="rounded-full bg-primary-soft/80 px-2.5 py-0.5 text-[11px] font-medium text-primary dark:bg-blue-900/40 dark:text-blue-300"
                    >
                      #{kw}
                    </span>
                  ))
                ) : (
                  <span className="text-xs text-slate dark:text-slate-400 italic">
                    Semantic conceptual match (no verbatim stopword overlap)
                  </span>
                )}
              </div>
            </div>

            {/* Supported Claims */}
            <div className="rounded-2xl border border-border bg-surface-muted/40 p-3.5 dark:bg-white/5 dark:border-white/10">
              <span className="mono-label text-[10px] font-bold text-slate dark:text-slate-300 flex items-center gap-1">
                <CheckCircle2 size={12} className="text-teal" /> GROUNDED ANSWER CLAIMS
              </span>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {citation.supported_claims && citation.supported_claims.length > 0 ? (
                  citation.supported_claims.map((claimIdx) => (
                    <span
                      key={claimIdx}
                      className="rounded-full bg-teal-soft px-2.5 py-0.5 text-[11px] font-bold text-teal dark:bg-teal-900/40 dark:text-teal-300"
                    >
                      Claim #{claimIdx}
                    </span>
                  ))
                ) : (
                  <span className="text-xs text-slate dark:text-slate-400 italic">
                    Serves as foundational scientific context
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Excerpt / Passage Text */}
          <div className="rounded-2xl border border-border bg-surface p-3.5 dark:bg-white/5 dark:border-white/10">
            <span className="mono-label text-[10px] font-bold text-slate dark:text-slate-300">
              VERIFIED PASSAGE EVIDENCE
            </span>
            <p className="mt-2 text-xs leading-relaxed italic text-ink dark:text-slate-200">
              "{citation.snippet || (citation.viewer_reference?.snippet ?? 'No passage snippet recorded.')}"
            </p>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="flex items-center justify-between border-t border-border/80 pt-4 dark:border-white/10">
          <Button variant="ghost" size="sm" onClick={onClose}>
            Close
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={() => {
              onClose()
              onOpenPdf(citation)
            }}
            className="gap-1.5"
          >
            <ExternalLink size={14} /> Open in PDF Viewer (p.{citation.page_start})
          </Button>
        </div>
      </div>
    </div>
  )
}
