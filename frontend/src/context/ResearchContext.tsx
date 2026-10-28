import React, { createContext, useContext, useEffect, useState, useCallback, useRef } from 'react'
import toast from 'react-hot-toast'
import {
  type KnowledgeScope,
  type IngestionJob,
  type PaperItem,
  listPapers,
  getIngestionStatus,
  listIngestionJobs,
} from '../services/api'

export interface PdfViewerState {
  isOpen: boolean
  paperId: string
  title: string
  page: number
  snippet?: string
  section?: string
  citationId?: string
}

export interface OnlineDiscoveryState {
  isOpen: boolean
  initialQuery: string
  onComplete?: () => void
}

interface ResearchContextValue {
  sessionId: string
  selectedScope: KnowledgeScope
  setSelectedScope: (scope: KnowledgeScope) => void
  selectedPaperId: string | null
  setSelectedPaperId: (id: string | null) => void
  selectedPaperTitle: string | null
  setSelectedPaperTitle: (title: string | null) => void
  setPaperIsolation: (paperId: string, paperTitle: string) => void
  papers: PaperItem[]
  isLoadingPapers: boolean
  refreshPapers: () => Promise<void>
  activeJobs: IngestionJob[]
  trackJob: (jobId: string) => void
  pdfViewer: PdfViewerState
  openPdfViewer: (opts: {
    paperId: string
    title: string
    page: number
    snippet?: string
    section?: string
    citationId?: string
  }) => void
  closePdfViewer: () => void
  onlineDiscovery: OnlineDiscoveryState
  openOnlineDiscovery: (initialQuery?: string, onComplete?: () => void) => void
  closeOnlineDiscovery: () => void
}

const ResearchContext = createContext<ResearchContextValue | undefined>(undefined)

const SESSION_STORAGE_KEY = 'lumina_session_id'

export function ResearchProvider({ children }: { children: React.ReactNode }) {
  // Session ID
  const [sessionId] = useState<string>(() => {
    const existing = localStorage.getItem(SESSION_STORAGE_KEY) || localStorage.getItem('researchmind_session_id')
    if (existing) {
      localStorage.setItem(SESSION_STORAGE_KEY, existing)
      return existing
    }
    const generated = `session_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`
    localStorage.setItem(SESSION_STORAGE_KEY, generated)
    return generated
  })

  // Selected Scope
  const [selectedScope, setSelectedScope] = useState<KnowledgeScope>('global')
  const [selectedPaperId, setSelectedPaperId] = useState<string | null>(null)
  const [selectedPaperTitle, setSelectedPaperTitle] = useState<string | null>(null)

  // Paper Catalog
  const [papers, setPapers] = useState<PaperItem[]>([])
  const [isLoadingPapers, setIsLoadingPapers] = useState<boolean>(false)

  // Ingestion Jobs
  const [activeJobs, setActiveJobs] = useState<IngestionJob[]>([])
  const pollingTimers = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map())

  // PDF Viewer Drawer State
  const [pdfViewer, setPdfViewer] = useState<PdfViewerState>({
    isOpen: false,
    paperId: '',
    title: '',
    page: 1,
  })

  // Online Discovery Modal State
  const [onlineDiscovery, setOnlineDiscovery] = useState<OnlineDiscoveryState>({
    isOpen: false,
    initialQuery: '',
  })

  // Load papers from backend
  const refreshPapers = useCallback(async () => {
    setIsLoadingPapers(true)
    try {
      const data = await listPapers(sessionId)
      setPapers(data.papers || [])
    } catch (err) {
      console.warn('Could not load papers from backend:', err)
    } finally {
      setIsLoadingPapers(false)
    }
  }, [sessionId])

  // Track Ingestion Job until finished
  const trackJob = useCallback(
    (jobId: string) => {
      // Clear any existing timer for this job
      const existingTimer = pollingTimers.current.get(jobId)
      if (existingTimer) clearTimeout(existingTimer)

      const poll = async () => {
        try {
          const job = await getIngestionStatus(jobId)
          setActiveJobs((prev) => {
            const idx = prev.findIndex((j) => j.job_id === jobId)
            if (idx >= 0) {
              const updated = [...prev]
              updated[idx] = job
              return updated
            }
            return [job, ...prev]
          })

          if (job.status === 'COMPLETED') {
            toast.success(`Ingestion complete: ${job.file_name}`, { icon: '📄' })
            pollingTimers.current.delete(jobId)
            refreshPapers()
            return
          }

          if (job.status === 'FAILED') {
            toast.error(`Ingestion failed: ${job.error_message || job.file_name}`, { icon: '⚠️' })
            pollingTimers.current.delete(jobId)
            return
          }

          // Continue polling
          const timer = setTimeout(poll, 1500)
          pollingTimers.current.set(jobId, timer)
        } catch (e) {
          console.error(`Error polling job ${jobId}:`, e)
          pollingTimers.current.delete(jobId)
        }
      }

      poll()
    },
    [refreshPapers]
  )

  // Initial load
  useEffect(() => {
    refreshPapers()
    // Load existing jobs
    listIngestionJobs(sessionId)
      .then((jobs) => {
        setActiveJobs(jobs)
        // Resume polling for uncompleted jobs
        jobs.forEach((job) => {
          if (job.status !== 'COMPLETED' && job.status !== 'FAILED') {
            trackJob(job.job_id)
          }
        })
      })
      .catch((e) => console.warn('Could not fetch ingestion jobs:', e))

    return () => {
      // Cleanup all polling timers on unmount
      pollingTimers.current.forEach((t) => clearTimeout(t))
      pollingTimers.current.clear()
    }
  }, [sessionId, refreshPapers, trackJob])

  const setPaperIsolation = useCallback((paperId: string, paperTitle: string) => {
    setSelectedScope('this_paper')
    setSelectedPaperId(paperId)
    setSelectedPaperTitle(paperTitle)
    toast.success(`Scope set to isolated paper: ${paperTitle}`, { icon: '🎯' })
  }, [])

  const openPdfViewer = useCallback(
    (opts: {
      paperId: string
      title: string
      page: number
      snippet?: string
      section?: string
      citationId?: string
    }) => {
      setPdfViewer({
        isOpen: true,
        paperId: opts.paperId,
        title: opts.title,
        page: opts.page,
        snippet: opts.snippet,
        section: opts.section,
        citationId: opts.citationId,
      })
    },
    []
  )

  const closePdfViewer = useCallback(() => {
    setPdfViewer((prev) => ({ ...prev, isOpen: false }))
  }, [])

  const openOnlineDiscovery = useCallback((initialQuery = '', onComplete?: () => void) => {
    setOnlineDiscovery({
      isOpen: true,
      initialQuery,
      onComplete,
    })
  }, [])

  const closeOnlineDiscovery = useCallback(() => {
    setOnlineDiscovery((prev) => ({ ...prev, isOpen: false }))
  }, [])

  return (
    <ResearchContext.Provider
      value={{
        sessionId,
        selectedScope,
        setSelectedScope,
        selectedPaperId,
        setSelectedPaperId,
        selectedPaperTitle,
        setSelectedPaperTitle,
        setPaperIsolation,
        papers,
        isLoadingPapers,
        refreshPapers,
        activeJobs,
        trackJob,
        pdfViewer,
        openPdfViewer,
        closePdfViewer,
        onlineDiscovery,
        openOnlineDiscovery,
        closeOnlineDiscovery,
      }}
    >
      {children}
    </ResearchContext.Provider>
  )
}

export function useResearch() {
  const context = useContext(ResearchContext)
  if (!context) {
    throw new Error('useResearch must be used within a ResearchProvider')
  }
  return context
}
