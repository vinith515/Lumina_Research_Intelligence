import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import { X, ExternalLink, Download, FileText, Bookmark, ChevronLeft, ChevronRight, Sparkles } from 'lucide-react'
import { useResearch } from '../../context/ResearchContext'
import { getPaperPdfUrl } from '../../services/api'
import { Badge, Button } from '../ui/Primitives'

export function PdfViewerDrawer() {
  const { pdfViewer, closePdfViewer } = useResearch()
  const [currentPage, setCurrentPage] = useState<number>(pdfViewer.page || 1)

  useEffect(() => {
    setCurrentPage(pdfViewer.page || 1)
  }, [pdfViewer.page, pdfViewer.paperId])

  if (!pdfViewer.isOpen) return null

  const pdfUrl = getPaperPdfUrl(pdfViewer.paperId, currentPage)
  const directPdfUrl = getPaperPdfUrl(pdfViewer.paperId)

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-[110] flex justify-end bg-black/60 backdrop-blur-sm">
        {/* Backdrop click to close */}
        <div className="absolute inset-0" onClick={closePdfViewer} />

        {/* Drawer container */}
        <motion.div
          initial={{ x: '100%' }}
          animate={{ x: 0 }}
          exit={{ x: '100%' }}
          transition={{ type: 'spring', damping: 28, stiffness: 280 }}
          className="relative z-10 flex h-full w-full max-w-5xl flex-col bg-surface shadow-2xl dark:bg-[#0d1527] border-l border-border"
        >
          {/* Top Bar */}
          <div className="flex items-center justify-between border-b border-border bg-canvas/80 px-6 py-4 backdrop-blur-xl">
            <div className="flex min-w-0 items-center gap-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary-soft text-primary">
                <FileText size={20} />
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  {pdfViewer.citationId && (
                    <Badge tone="violet">Citation [{pdfViewer.citationId}]</Badge>
                  )}
                  <span className="mono-label text-[10px] text-slate">PDF Source Grounding</span>
                </div>
                <h3 className="truncate font-display text-lg font-semibold text-ink sm:text-xl" title={pdfViewer.title}>
                  {pdfViewer.title || 'Research Document'}
                </h3>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {/* Page navigation controls */}
              <div className="flex items-center gap-1 rounded-full border border-border bg-surface px-2 py-1">
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7"
                  disabled={currentPage <= 1}
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  aria-label="Previous page"
                >
                  <ChevronLeft size={14} />
                </Button>
                <span className="px-2 text-xs font-semibold text-ink">Page {currentPage}</span>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7"
                  onClick={() => setCurrentPage((p) => p + 1)}
                  aria-label="Next page"
                >
                  <ChevronRight size={14} />
                </Button>
              </div>

              <a
                href={directPdfUrl}
                target="_blank"
                rel="noreferrer"
                className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-border bg-surface text-slate transition hover:text-primary"
                title="Open PDF in new tab"
              >
                <ExternalLink size={15} />
              </a>

              <a
                href={directPdfUrl}
                download
                className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-border bg-surface text-slate transition hover:text-primary"
                title="Download original PDF"
              >
                <Download size={15} />
              </a>

              <Button
                variant="ghost"
                size="icon"
                onClick={closePdfViewer}
                className="h-9 w-9"
                aria-label="Close PDF Viewer"
              >
                <X size={18} />
              </Button>
            </div>
          </div>

          {/* Drawer Body - Split View */}
          <div className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-[380px_minmax(0,1fr)]">
            {/* Left side: Cited Passage & Provenance */}
            <div className="flex flex-col border-b border-border bg-surface-muted/50 p-6 lg:border-b-0 lg:border-r lg:overflow-y-auto">
              <div className="flex items-center gap-2 text-primary">
                <Bookmark size={16} />
                <span className="mono-label text-xs font-semibold">Cited Passage & Provenance</span>
              </div>

              {pdfViewer.section && (
                <div className="mt-4 rounded-xl border border-border bg-surface p-3">
                  <p className="text-[10px] uppercase tracking-wider text-slate font-semibold">Section</p>
                  <p className="mt-0.5 text-xs font-bold text-ink">{pdfViewer.section}</p>
                  <p className="mt-1 text-[10px] text-slate">Grounded at Page {pdfViewer.page}</p>
                </div>
              )}

              {pdfViewer.snippet ? (
                <div className="mt-4 flex-1">
                  <div className="rounded-2xl border border-violet/20 bg-violet-soft/40 p-4">
                    <div className="mb-2 flex items-center justify-between">
                      <span className="text-[10px] font-bold uppercase tracking-widest text-violet">
                        Extracted Supporting Evidence
                      </span>
                      <Sparkles size={12} className="text-violet" />
                    </div>
                    <blockquote className="text-xs leading-relaxed text-ink italic font-serif">
                      "{pdfViewer.snippet}"
                    </blockquote>
                  </div>
                </div>
              ) : (
                <div className="mt-4 rounded-2xl border border-border bg-surface p-4 text-xs text-slate">
                  Viewing full document context for this research paper. Navigate pages using the toolbar above.
                </div>
              )}

              <div className="mt-6 rounded-2xl border border-border/80 bg-surface/60 p-4 text-[11px] text-slate space-y-2">
                <p className="font-semibold text-ink">Navigation Tips:</p>
                <ul className="list-disc pl-4 space-y-1">
                  <li>Use the page arrows above to flip directly to adjacent pages.</li>
                  <li>Click the external link icon to open the native browser PDF reader.</li>
                  <li>Gemini responses cite directly to these structured document elements.</li>
                </ul>
              </div>
            </div>

            {/* Right side: Interactive PDF View via iframe */}
            <div className="relative min-h-[400px] flex-1 bg-slate-900/10 p-2">
              <iframe
                key={`${pdfViewer.paperId}-${currentPage}`}
                src={pdfUrl}
                className="h-full w-full rounded-2xl border border-border bg-white shadow-inner"
                title={`PDF Document - ${pdfViewer.title}`}
              />
            </div>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  )
}
