import { useState, useRef, type DragEvent } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import {
  CloudUpload,
  FileText,
  LoaderCircle,
  CheckCircle2,
  AlertCircle,
  Database,
  Clock,
  ShieldCheck,
  Info,
  RefreshCw,
  MessageSquare,
  X,
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { useResearch } from '../context/ResearchContext'
import { useAuth } from '../context/AuthContext'
import { uploadPaper, type IngestionJob } from '../services/api'
import { Badge, Button, GlassCard, SectionHeader, cn } from '../components/ui/Primitives'

const STAGE_LABELS: Record<string, string> = {
  PENDING: 'Queued for Ingestion',
  DOWNLOADING: 'Downloading PDF',
  DOWNLOADED: 'Download Completed',
  PARSING: 'Extracting PDF Elements (Unstructured)',
  CHUNKING: 'Semantic Chunking by Section',
  EMBEDDING: 'Generating Dense Embeddings (SciBERT)',
  INDEXING: 'Indexing to Vector DB & BM25',
  COMPLETED: 'Ingestion Completed & Ready',
  FAILED: 'Processing Failed',
}

const STAGES_LIST = ['PARSING', 'CHUNKING', 'EMBEDDING', 'INDEXING', 'COMPLETED']

export function UploadPage() {
  const navigate = useNavigate()
  const { sessionId, trackJob, activeJobs, setPaperIsolation } = useResearch()
  const { user } = useAuth()
  const inputRef = useRef<HTMLInputElement>(null)

  const [dragging, setDragging] = useState(false)
  const [isUploading, setIsUploading] = useState(false)

  // Ingestion Destination prompt state (Requirements: ask every time)
  const [pendingFiles, setPendingFiles] = useState<File[] | null>(null)
  const [showChoiceModal, setShowChoiceModal] = useState(false)
  const [chosenMode, setChosenMode] = useState<'permanent' | 'session_only'>('permanent')

  function handleFiles(files: FileList | null) {
    if (!files || files.length === 0) return

    const validFiles: File[] = []
    for (let i = 0; i < files.length; i++) {
      const file = files[i]
      if (!file.name.toLowerCase().endsWith('.pdf') && file.type !== 'application/pdf') {
        toast.error(`"${file.name}" is not a PDF file. Only PDF documents are supported.`)
        continue
      }
      if (file.size > 50 * 1024 * 1024) {
        toast.error(`"${file.name}" exceeds the 50 MB limit.`)
        continue
      }
      validFiles.push(file)
    }

    if (validFiles.length === 0) return

    // Ask user every time before starting upload/ingestion
    setPendingFiles(validFiles)
    setShowChoiceModal(true)
  }

  async function executeUpload() {
    if (!pendingFiles || pendingFiles.length === 0) return

    setShowChoiceModal(false)
    setIsUploading(true)

    for (const file of pendingFiles) {
      try {
        const res = await uploadPaper(file, sessionId, chosenMode, user?.email)
        const modeLabel = chosenMode === 'permanent' ? 'Permanent Database' : 'Session Only'
        toast.success(`Uploaded "${file.name}" (${modeLabel}). Ingestion started!`, { icon: '📄' })
        trackJob(res.job_id)
      } catch (err: any) {
        console.error('Upload error:', err)
        toast.error(`Failed to upload "${file.name}": ${err?.response?.data?.detail || err.message}`)
      }
    }

    setIsUploading(false)
    setPendingFiles(null)
    if (inputRef.current) {
      inputRef.current.value = ''
    }
  }

  function onDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault()
    setDragging(false)
    handleFiles(e.dataTransfer.files)
  }

  function handleAskAboutPaper(job: IngestionJob) {
    if (!job.paper_id) return
    const title = job.title || job.file_name.replace('.pdf', '')
    setPaperIsolation(job.paper_id, title)
    navigate('/app/chat')
  }

  // Filter jobs for current session or recent uploads
  const userUploadJobs = activeJobs.filter(
    (j: IngestionJob) => j.source === 'user_upload' || j.scope === 'user' || j.session_id === sessionId
  )

  const pendingOrProcessingCount = userUploadJobs.filter(
    (j: IngestionJob) => j.status !== 'COMPLETED' && j.status !== 'FAILED'
  ).length

  return (
    <div className="space-y-8">
      <SectionHeader
        eyebrow="Dynamic Corpus Ingestion"
        title="Upload Research Papers"
        description="Ingest PDFs directly into your knowledge base or temporary session. The document is parsed by Unstructured, chunked with section awareness, embedded with SciBERT, and indexed for grounded RAG."
      />

      <div className="grid gap-6 xl:grid-cols-[1.25fr_0.75fr]">
        <div className="space-y-6">
          {/* Drag & Drop Upload Target */}
          <div
            className={cn(
              'glass-panel rounded-[2rem] border-2 border-dashed p-8 text-center transition sm:p-12',
              dragging
                ? 'border-primary bg-primary-soft/60 dark:bg-primary/20'
                : 'border-border hover:border-primary/40'
            )}
            onDragEnter={(e) => {
              e.preventDefault()
              setDragging(true)
            }}
            onDragOver={(e) => e.preventDefault()}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
          >
            <motion.div
              animate={{ scale: dragging ? 1.08 : 1 }}
              className="mx-auto flex h-20 w-20 items-center justify-center rounded-3xl bg-primary-soft text-primary dark:bg-blue-900/40 dark:text-blue-300"
            >
              {isUploading ? (
                <LoaderCircle size={36} className="animate-spin text-primary dark:text-blue-300" />
              ) : (
                <CloudUpload size={36} />
              )}
            </motion.div>

            <h2 className="mt-5 font-display text-3xl font-semibold text-ink sm:text-4xl">
              {isUploading ? 'Uploading & Ingesting Papers...' : 'Drop PDF Papers Here'}
            </h2>
            <p className="mx-auto mt-2 max-w-sm text-sm text-slate dark:text-slate-300">
              Drag and drop your research PDFs, or browse local files. You will be prompted to choose permanent database ingestion or temporary session isolation.
            </p>

            <input
              ref={inputRef}
              type="file"
              accept=".pdf,application/pdf"
              multiple
              className="hidden"
              onChange={(e) => handleFiles(e.target.files)}
            />

            <Button
              className="mt-6"
              variant="primary"
              disabled={isUploading}
              onClick={() => inputRef.current?.click()}
            >
              {isUploading ? (
                <>
                  <LoaderCircle size={15} className="animate-spin" /> Processing...
                </>
              ) : (
                'Browse Local Files'
              )}
            </Button>

            <div className="mt-6 flex flex-wrap justify-center gap-4 text-[10px] font-bold uppercase tracking-[0.12em] text-slate dark:text-slate-300">
              <span className="flex items-center gap-1.5">
                <FileText size={13} className="text-primary dark:text-blue-400" /> PDF only
              </span>
              <span className="flex items-center gap-1.5">
                <Database size={13} className="text-teal dark:text-teal-400" /> Up to 50 MB
              </span>
              <span className="flex items-center gap-1.5">
                <ShieldCheck size={13} className="text-violet dark:text-purple-400" /> Choose Target Scope
              </span>
            </div>
          </div>

          {/* Active Ingestion Job Status Section */}
          <GlassCard className="p-5 sm:p-6">
            <div className="mb-5 flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
              <div>
                <h3 className="flex items-center gap-2 font-display text-2xl font-semibold text-ink">
                  <LoaderCircle
                    className={
                      pendingOrProcessingCount > 0
                        ? 'animate-spin text-primary dark:text-blue-400'
                        : 'text-teal dark:text-teal-400'
                    }
                    size={20}
                  />
                  Live Ingestion Queue
                </h3>
                <p className="text-xs text-slate dark:text-slate-300 mt-0.5">
                  Real-time status reported by the Celery ingestion worker
                </p>
              </div>

              <Badge tone={pendingOrProcessingCount > 0 ? 'primary' : 'teal'}>
                {pendingOrProcessingCount > 0
                  ? `${pendingOrProcessingCount} Processing`
                  : 'All Jobs Complete'}
              </Badge>
            </div>

            {userUploadJobs.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-border p-8 text-center text-xs text-slate dark:text-slate-300">
                No papers uploaded in this session yet. Upload a PDF above to track its live parsing and indexing.
              </div>
            ) : (
              <div className="space-y-4">
                {userUploadJobs.map((job: IngestionJob) => {
                  const isCompleted = job.status === 'COMPLETED'
                  const isFailed = job.status === 'FAILED'
                  const title = job.title || job.file_name.replace('.pdf', '').replace(/_/g, ' ')

                  return (
                    <div
                      key={job.job_id}
                      className="rounded-2xl border border-border bg-surface p-4 shadow-xs dark:bg-white/5"
                    >
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                        <div className="flex items-start gap-3 min-w-0">
                          <div
                            className={cn(
                              'mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl',
                              isCompleted
                                ? 'bg-teal-soft text-teal dark:bg-teal-900/40 dark:text-teal-300'
                                : isFailed
                                ? 'bg-danger-soft text-danger dark:bg-red-900/40 dark:text-red-300'
                                : 'bg-primary-soft text-primary dark:bg-blue-900/40 dark:text-blue-300'
                            )}
                          >
                            <FileText size={18} />
                          </div>

                          <div className="min-w-0 flex-1">
                            <div className="flex items-center gap-2">
                              <h4 className="truncate text-sm font-bold text-ink" title={title}>
                                {title}
                              </h4>
                              {job.scope && (
                                <Badge tone={job.scope === 'global' ? 'primary' : 'violet'}>
                                  {job.scope === 'global' ? 'Database' : 'Session'}
                                </Badge>
                              )}
                            </div>
                            <p className="mt-0.5 text-xs text-slate dark:text-slate-300">
                              {job.status_message || STAGE_LABELS[job.status] || job.status}
                            </p>
                          </div>
                        </div>

                        <div className="flex items-center gap-2 self-end sm:self-center">
                          <Badge
                            tone={isCompleted ? 'teal' : isFailed ? 'danger' : 'primary'}
                          >
                            {isCompleted ? 'Completed' : isFailed ? 'Failed' : job.status}
                          </Badge>

                          {isCompleted && (
                            <Button
                              variant="primary"
                              size="sm"
                              onClick={() => handleAskAboutPaper(job)}
                              className="text-xs"
                            >
                              <MessageSquare size={13} /> Ask About This Paper
                            </Button>
                          )}

                          {isFailed && (
                            <Button
                              variant="danger"
                              size="sm"
                              onClick={() => trackJob(job.job_id)}
                              className="text-xs"
                            >
                              <RefreshCw size={13} /> Retry
                            </Button>
                          )}
                        </div>
                      </div>

                      {/* Progress Bar & Stage Indicator */}
                      <div className="mt-3">
                        <div className="h-1.5 overflow-hidden rounded-full bg-border dark:bg-white/10">
                          <div
                            className={cn(
                              'h-full rounded-full transition-all duration-500',
                              isCompleted
                                ? 'w-full bg-teal dark:bg-teal-400'
                                : isFailed
                                ? 'w-full bg-danger dark:bg-red-400'
                                : 'bg-gradient-to-r from-primary to-violet'
                            )}
                            style={{
                              width: isCompleted
                                ? '100%'
                                : isFailed
                                ? '100%'
                                : `${Math.max(10, job.progress_percent || 30)}%`,
                            }}
                          />
                        </div>

                        {/* Stage Pills */}
                        <div className="mt-3 grid grid-cols-2 sm:grid-cols-5 gap-1.5 text-[10px]">
                          {[
                            { key: 'PARSING', label: '1. Parsing' },
                            { key: 'CHUNKING', label: '2. Chunking' },
                            { key: 'EMBEDDING', label: '3. Embedding' },
                            { key: 'INDEXING', label: '4. Indexing' },
                            { key: 'COMPLETED', label: '5. Ready' },
                          ].map((stage, idx) => {
                            const curIdx = STAGES_LIST.indexOf(job.status)
                            const isPast = isCompleted || curIdx > idx
                            const isCurrent = curIdx === idx && !isCompleted

                            return (
                              <div
                                key={stage.key}
                                className={cn(
                                  'rounded-lg px-2 py-1 text-center font-medium border transition',
                                  isPast
                                    ? 'border-teal/30 bg-teal-soft/50 text-teal dark:bg-teal-900/30 dark:text-teal-300'
                                    : isCurrent
                                    ? 'border-primary/40 bg-primary-soft text-primary animate-pulse font-bold dark:bg-blue-900/40 dark:text-blue-300'
                                    : 'border-border bg-surface-muted/50 text-slate/60 dark:bg-white/5 dark:text-slate-400'
                                )}
                              >
                                {stage.label}
                              </div>
                            )
                          })}
                        </div>

                        {isCompleted && job.chunk_count > 0 && (
                          <div className="mt-2.5 flex items-center justify-between text-[11px] text-teal dark:text-teal-300 font-semibold">
                            <span className="flex items-center gap-1">
                              <CheckCircle2 size={13} /> {job.chunk_count} semantic chunks indexed
                            </span>
                            <span className="text-slate dark:text-slate-400 font-normal">
                              Indexed in {job.scope === 'global' ? 'Global Database' : 'Session Scope'}
                            </span>
                          </div>
                        )}

                        {isFailed && job.error && (
                          <div className="mt-2.5 flex items-center gap-1.5 text-[11px] text-danger dark:text-red-400">
                            <AlertCircle size={13} /> Error: {job.error}
                          </div>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </GlassCard>
        </div>

        {/* Sidebar Information */}
        <div className="space-y-6">
          <div className="relative overflow-hidden rounded-[2rem] bg-gradient-to-br from-violet to-primary p-6 text-white shadow-lg">
            <div className="relative">
              <Info className="text-white/80" size={20} />
              <h3 className="mt-4 font-display text-2xl font-bold">
                Dynamic Ingestion Architecture
              </h3>
              <p className="mt-2 text-xs leading-relaxed text-white/80">
                Uploaded papers are processed via Celery background tasks with strict multi-tenant session isolation or permanent database cataloging.
              </p>

              <ul className="mt-4 space-y-2.5 text-xs text-white/80">
                <li className="flex items-center gap-2">
                  <CheckCircle2 size={14} className="text-teal-300" />
                  <span>Unstructured PDF element extraction</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 size={14} className="text-teal-300" />
                  <span>Title & section hierarchical chunking</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 size={14} className="text-teal-300" />
                  <span>768-dim SciBERT dense embeddings</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 size={14} className="text-teal-300" />
                  <span>Dual ChromaDB + BM25 indexing</span>
                </li>
              </ul>
            </div>
          </div>

          <GlassCard className="p-6">
            <h3 className="font-display text-xl font-bold text-ink">
              Permanent vs Temporary Ingestion
            </h3>
            <p className="mt-2 text-xs text-slate dark:text-slate-300 leading-relaxed">
              When uploading papers, you can choose to store them permanently in the shared database
              for cross-session search, or keep them temporary for your active session only.
            </p>
          </GlassCard>
        </div>
      </div>

      {/* Confirmation Modal: Ingest to Database vs Session Only */}
      <AnimatePresence>
        {showChoiceModal && pendingFiles && (
          <div className="fixed inset-0 z-[120] flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="w-full max-w-lg rounded-3xl bg-surface p-6 sm:p-8 shadow-2xl border border-border dark:bg-[#10182c] dark:border-white/15"
            >
              <div className="flex items-center justify-between border-b border-border dark:border-white/10 pb-4">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-violet text-white shadow-sm">
                    <Database size={20} />
                  </div>
                  <div>
                    <h3 className="font-display text-2xl font-bold text-ink">
                      Choose Ingestion Target
                    </h3>
                    <p className="text-xs text-slate dark:text-slate-300">
                      {pendingFiles.length} paper{pendingFiles.length > 1 ? 's' : ''} ready for processing
                    </p>
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => {
                    setShowChoiceModal(false)
                    setPendingFiles(null)
                  }}
                  aria-label="Close dialog"
                >
                  <X size={18} />
                </Button>
              </div>

              <div className="mt-5 space-y-4">
                <p className="text-xs text-slate dark:text-slate-300">
                  Where would you like to ingest these papers? Lumina asks you every time so you have complete control over your corpus:
                </p>

                {/* Option 1: Permanent Database */}
                <div
                  onClick={() => setChosenMode('permanent')}
                  className={cn(
                    'cursor-pointer rounded-2xl border p-4 transition-all',
                    chosenMode === 'permanent'
                      ? 'border-primary bg-primary-soft/50 ring-2 ring-primary/20 dark:bg-blue-950/40 dark:border-blue-500/60'
                      : 'border-border bg-surface-muted/40 hover:border-primary/40 dark:bg-white/5 dark:border-white/10'
                  )}
                >
                  <div className="flex items-start gap-3">
                    <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-primary text-white shadow-xs">
                      <Database size={16} />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between gap-2">
                        <h4 className="text-sm font-bold text-ink">
                          Permanent Database (Corpus)
                        </h4>
                        <Badge tone="teal">Persistent</Badge>
                      </div>
                      <p className="mt-1 text-xs text-slate dark:text-slate-300 leading-relaxed">
                        Store and index into the shared knowledge base database. Papers remain permanently accessible across all sessions, future projects, and global queries.
                      </p>
                    </div>
                  </div>
                </div>

                {/* Option 2: Active Session Only */}
                <div
                  onClick={() => setChosenMode('session_only')}
                  className={cn(
                    'cursor-pointer rounded-2xl border p-4 transition-all',
                    chosenMode === 'session_only'
                      ? 'border-violet bg-violet-soft/50 ring-2 ring-violet/20 dark:bg-purple-950/40 dark:border-purple-500/60'
                      : 'border-border bg-surface-muted/40 hover:border-violet/40 dark:bg-white/5 dark:border-white/10'
                  )}
                >
                  <div className="flex items-start gap-3">
                    <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-violet text-white shadow-xs">
                      <Clock size={16} />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between gap-2">
                        <h4 className="text-sm font-bold text-ink">
                          Session Only (Temporary)
                        </h4>
                        <Badge tone="violet">Isolated</Badge>
                      </div>
                      <p className="mt-1 text-xs text-slate dark:text-slate-300 leading-relaxed">
                        Index strictly for this active session only. Does not write to the permanent database, keeping your workspace clean and isolated.
                      </p>
                    </div>
                  </div>
                </div>

                {/* Files to Ingest preview list */}
                <div className="rounded-xl border border-border bg-surface-muted/50 p-3 dark:bg-white/5 dark:border-white/10">
                  <p className="mono-label text-[10px] text-slate dark:text-slate-300 mb-1.5">
                    Selected Files:
                  </p>
                  <div className="max-h-24 overflow-y-auto space-y-1">
                    {pendingFiles.map((f, i) => (
                      <div key={i} className="flex items-center justify-between text-xs text-ink font-medium">
                        <span className="truncate max-w-[320px]">{f.name}</span>
                        <span className="text-[10px] text-slate dark:text-slate-400">
                          {(f.size / (1024 * 1024)).toFixed(2)} MB
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Action buttons */}
              <div className="mt-6 flex items-center justify-end gap-3 pt-3 border-t border-border dark:border-white/10">
                <Button
                  variant="ghost"
                  onClick={() => {
                    setShowChoiceModal(false)
                    setPendingFiles(null)
                  }}
                >
                  Cancel
                </Button>
                <Button
                  variant="primary"
                  onClick={executeUpload}
                >
                  Confirm & Ingest Papers
                </Button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  )
}
