import { useState, useRef, useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import {
  Sparkles,
  Send,
  RefreshCw,
  Bookmark,
  ExternalLink,
  LoaderCircle,
  AlertCircle,
  Globe,
  FileText,
  Clock,
  Layers,
  CheckCircle2,
  Search,
  ShieldCheck,
  BarChart3,
  ArrowUpRight,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { useResearch } from '../context/ResearchContext'
import { useAuth } from '../context/AuthContext'
import {
  executeQuery,
  type StructuredCitation,
  type SourceChunk,
  type KnowledgeScope,
  type XAIExplanation,
  type ComponentQualityAssessment,
} from '../services/api'
import { ScopeSelector, SCOPE_OPTIONS } from '../components/scope/ScopeSelector'
import { Button, GlassCard, Badge, CopyButton } from '../components/ui/Primitives'
import { CitationInspectorModal } from '../components/xai/CitationInspectorModal'
import { XaiAuditModal } from '../components/xai/XaiAuditModal'

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  latencyMs?: number
  evidenceState?: string
  abstained?: boolean
  onlineSearchSuggested?: boolean
  suggestedQuery?: string | null
  knowledgeScope?: KnowledgeScope
  structuredCitations?: StructuredCitation[]
  sources?: SourceChunk[]
  targetPaperId?: string | null
  targetPaperTitle?: string | null
  faithfulnessScore?: number | null
  xaiExplanation?: XAIExplanation | null
  componentAssessment?: ComponentQualityAssessment | null
}

const DEFAULT_QUESTIONS = [
  'What are the key trade-offs between dense retrieval and BM25 lexical search in Lumina?',
  'How does FlashAttention avoid the quadratic memory overhead of standard self-attention?',
  'Explain how dynamic routing and isolation prevent cross-corpus contamination in private research papers.',
  'What embedding model does Lumina use for scientific paper chunking and indexing?',
]

export function ChatPage() {
  const {
    sessionId,
    selectedScope,
    selectedPaperId,
    selectedPaperTitle,
    openPdfViewer,
    openOnlineDiscovery,
    papers,
  } = useResearch()

  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome-msg',
      role: 'assistant',
      content: `Welcome to **Lumina**. I am your grounded scientific research assistant.

Every answer is strictly synthesized from peer-reviewed literature and user-uploaded papers using hybrid vector + lexical retrieval, re-ranking, and the Gemini API.

- Select your **Retrieval Scope** below to isolate sources.
- Click any citation marker like **[C1]** to open the source PDF directly to the cited page.
- If existing papers lack sufficient evidence, I will offer online discovery across **arXiv** and **Semantic Scholar**.`,
      timestamp: 'Just now',
    },
  ])

  const [draft, setDraft] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [activeSufficiencyAlert, setActiveSufficiencyAlert] = useState<{
    suggestedQuery: string
    originalQuestion: string
  } | null>(null)
  const [selectedXaiModalMessage, setSelectedXaiModalMessage] = useState<ChatMessage | null>(null)
  const [inspectingCitation, setInspectingCitation] = useState<StructuredCitation | null>(null)

  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, isLoading, activeSufficiencyAlert])

  const location = useLocation()
  const { user } = useAuth()

  useEffect(() => {
    if (location.state && (location.state as any).initialQuery) {
      const q = (location.state as any).initialQuery
      setDraft(q)
      window.history.replaceState({}, document.title)
    }
  }, [location.state])

  async function handleSend(queryText = draft) {
    const text = queryText.trim()
    if (!text || isLoading) return

    // Dismiss existing sufficiency alert
    setActiveSufficiencyAlert(null)

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    }

    setMessages((prev) => [...prev, userMsg])
    setDraft('')
    setIsLoading(true)

    try {
      // Extract recent dialogue turns for context-aware multi-turn resolution
      const historyPayload = messages
        .filter((m) => m.id !== 'welcome-msg')
        .slice(-10)
        .map((m) => ({
          role: m.role,
          content: m.content,
          target_paper_id: m.targetPaperId,
          target_paper_title: m.targetPaperTitle,
        }))

      const res = await executeQuery({
        query: text,
        knowledge_scope: selectedScope,
        scope_paper_ids: selectedPaperId ? [selectedPaperId] : undefined,
        session_id: sessionId,
        user_email: user?.email,
        top_k: 5,
        retrieval_mode: 'hybrid_rerank',
        conversation_history: historyPayload,
      })

      const assistantMsg: ChatMessage = {
        id: `asst-${Date.now()}`,
        role: 'assistant',
        content: res.answer,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        latencyMs: res.latency_ms,
        evidenceState: res.evidence_state,
        abstained: res.abstained,
        onlineSearchSuggested: res.online_search_suggested,
        suggestedQuery: res.suggested_query,
        knowledgeScope: res.knowledge_scope,
        structuredCitations: res.structured_citations,
        sources: res.sources,
        targetPaperId: res.target_paper_id,
        targetPaperTitle: res.target_paper_title,
        faithfulnessScore: res.faithfulness_score,
        xaiExplanation: res.xai_explanation,
        componentAssessment: res.component_assessment,
      }

      setMessages((prev) => [...prev, assistantMsg])

      // Check for evidence insufficiency
      if (res.online_search_suggested || res.abstained) {
        setActiveSufficiencyAlert({
          suggestedQuery: res.suggested_query || text,
          originalQuestion: text,
        })
      }
    } catch (err: any) {
      console.error('Error during research query execution:', err)
      toast.error('Failed to generate answer. Ensure backend is running.')
      setMessages((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          role: 'assistant',
          content: `⚠️ **Error communicating with Lumina backend:** ${
            err?.response?.data?.detail || err.message || 'Unknown network error.'
          }\n\nPlease verify that the FastAPI backend is running at \`http://127.0.0.1:8000\`.`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ])
    } finally {
      setIsLoading(false)
    }
  }

  function handleCitationClick(citation: StructuredCitation) {
    const page = citation.viewer_reference?.page || citation.page_start || 1
    openPdfViewer({
      paperId: citation.paper_id,
      title: citation.title,
      page,
      snippet: citation.snippet,
      section: citation.section,
      citationId: citation.citation_id,
    })
  }

  function handleStartOnlineSearch() {
    if (!activeSufficiencyAlert) return
    const q = activeSufficiencyAlert.suggestedQuery || activeSufficiencyAlert.originalQuestion
    openOnlineDiscovery(q, () => {
      // Callback after papers ingested: re-run question
      handleSend(activeSufficiencyAlert.originalQuestion)
    })
    setActiveSufficiencyAlert(null)
  }

  function clearChat() {
    setMessages([])
    setActiveSufficiencyAlert(null)
    toast.success('Conversation cleared.')
  }

  // Find latest response metrics for active context panel
  const latestAssistant = [...messages].reverse().find((m) => m.role === 'assistant')
  const currentScopeOpt = SCOPE_OPTIONS.find((o) => o.id === selectedScope) || SCOPE_OPTIONS[2]

  return (
    <div className="-mx-4 -my-7 flex min-h-[calc(100vh-76px)] flex-col overflow-hidden lg:-mx-10 lg:-my-10">
      {/* Top Context Bar */}
      <div className="flex items-center justify-between border-b border-border bg-canvas/80 px-4 py-3.5 backdrop-blur-xl sm:px-6">
        <div className="flex min-w-0 items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary text-white shadow-sm">
            <Sparkles size={17} />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-display text-sm font-bold text-ink">
                ResearchMind Intelligence Core
              </span>
              <span className="rounded-full bg-teal-soft px-2 py-0.5 text-[9px] font-bold text-teal">
                Gemini 2.5
              </span>
            </div>
            <p className="flex items-center gap-1.5 text-[10px] text-slate truncate">
              <span className="h-1.5 w-1.5 rounded-full bg-teal" />
              Scope:{' '}
              <strong className="text-ink font-semibold">{currentScopeOpt.label}</strong>
              {selectedScope === 'this_paper' && selectedPaperTitle && (
                <span className="truncate max-w-[220px]">({selectedPaperTitle})</span>
              )}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => openOnlineDiscovery()}
            className="text-xs text-primary hover:bg-primary-soft"
          >
            <Globe size={14} /> <span className="hidden sm:inline">Search Online</span>
          </Button>

          <Button variant="ghost" size="sm" onClick={clearChat}>
            <RefreshCw size={14} /> <span className="hidden sm:inline">Clear</span>
          </Button>
        </div>
      </div>

      {/* Main Split Body */}
      <div className="grid min-h-0 flex-1 xl:grid-cols-[minmax(0,1fr)_340px]">
        {/* Chat Stream & Input Area */}
        <div className="flex min-h-0 flex-col">
          {/* Scrollable Conversation Stream */}
          <div className="flex-1 overflow-y-auto px-4 py-7 sm:px-6 lg:px-8">
            <div className="mx-auto max-w-3xl space-y-6">
              {messages.length === 0 && (
                <div className="space-y-6 py-4">
                  {/* ResearchMind Domains Showcase Card */}
                  <div className="rounded-[2rem] border border-primary/20 bg-gradient-to-br from-primary-soft/50 via-surface to-violet-soft/30 p-6 sm:p-8 shadow-sm dark:from-[#0c1527] dark:via-[#10182c] dark:to-[#171438] dark:border-white/10">
                    <div className="flex items-center gap-2.5 mb-3">
                      <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-primary text-white shadow-xs">
                        <Sparkles size={16} />
                      </div>
                      <span className="mono-label text-xs font-bold text-primary dark:text-blue-400">
                        RESEARCHMIND DOMAIN KNOWLEDGE CORE
                      </span>
                    </div>

                    <h2 className="font-display text-2xl sm:text-3xl font-bold text-ink dark:text-white">
                      Ask Questions Across Our 5 Core AI Domains
                    </h2>
                    <p className="mt-2 text-xs sm:text-sm leading-relaxed text-slate dark:text-slate-300 max-w-2xl">
                      ResearchMind is pre-indexed with <strong className="text-ink dark:text-white">316 peer-reviewed papers</strong> across 5 dedicated computer science domains. Responses include strict inline citations with page coordinates.
                    </p>

                    <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                      {[
                        {
                          domain: 'Computer Vision',
                          abbr: 'CV',
                          icon: '👁️',
                          count: 80,
                          prompt: 'What are the main architectures used for multimodal industrial anomaly detection?',
                        },
                        {
                          domain: 'Deep Learning',
                          abbr: 'DL',
                          icon: '🧠',
                          count: 73,
                          prompt: 'How does parameter-efficient fine-tuning (LoRA) reduce GPU memory during model training?',
                        },
                        {
                          domain: 'Generative AI',
                          abbr: 'GenAI',
                          icon: '✨',
                          count: 66,
                          prompt: 'What techniques prevent hallucination in generative diffusion and multimodal LLMs?',
                        },
                        {
                          domain: 'Machine Learning',
                          abbr: 'ML',
                          icon: '⚙️',
                          count: 48,
                          prompt: 'Compare tree-based gradient boosting performance against neural networks on tabular datasets.',
                        },
                        {
                          domain: 'Natural Language Processing',
                          abbr: 'NLP',
                          icon: '💬',
                          count: 49,
                          prompt: 'How do sparse and flash attention mechanisms scale transformer context windows?',
                        },
                      ].map((item) => (
                        <button
                          key={item.domain}
                          type="button"
                          onClick={() => handleSend(item.prompt)}
                          className="group flex flex-col justify-between rounded-2xl border border-border bg-surface p-4 text-left transition hover:border-primary/50 hover:shadow-md dark:bg-white/5 dark:border-white/10 dark:hover:border-blue-400/50 cursor-pointer"
                        >
                          <div>
                            <div className="flex items-center justify-between">
                              <span className="text-lg">{item.icon}</span>
                              <span className="rounded-full bg-primary-soft px-2 py-0.5 text-[10px] font-bold text-primary dark:bg-blue-900/40 dark:text-blue-300">
                                {item.count} papers
                              </span>
                            </div>
                            <h4 className="mt-2.5 font-display text-sm font-bold text-ink transition group-hover:text-primary dark:text-white dark:group-hover:text-blue-300">
                              {item.domain}
                            </h4>
                            <p className="mt-1 text-[11px] leading-relaxed text-slate line-clamp-2 dark:text-slate-400">
                              "{item.prompt}"
                            </p>
                          </div>
                          <div className="mt-3 flex items-center gap-1 text-[10px] font-semibold text-primary opacity-0 group-hover:opacity-100 transition dark:text-blue-400">
                            <span>Ask this query</span>
                            <ArrowUpRight size={12} />
                          </div>
                        </button>
                      ))}
                    </div>

                    <div className="mt-5 flex items-center justify-between gap-3 rounded-xl bg-surface-muted/60 p-3.5 text-xs border border-border/80 dark:bg-white/5 dark:border-white/10">
                      <div className="flex items-center gap-2 text-slate dark:text-slate-300">
                        <Globe size={15} className="text-primary dark:text-blue-400 shrink-0" />
                        <span>
                          Outside these 5 domains? Use <strong>Online Discovery</strong> to search & ingest arXiv & Semantic Scholar literature on demand.
                        </span>
                      </div>
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => openOnlineDiscovery()}
                        className="text-xs shrink-0"
                      >
                        Search Online
                      </Button>
                    </div>
                  </div>
                </div>
              )}

              {messages.map((message) => {
                if (message.role === 'user') {
                  return (
                    <div key={message.id} className="flex justify-end">
                      <div className="max-w-[85%] rounded-3xl rounded-tr-sm bg-primary px-5 py-3.5 text-sm leading-relaxed text-white shadow-md dark:bg-blue-600 dark:text-white">
                        {message.content}
                        <div className="mt-1 text-right text-[10px] text-white/80">
                          {message.timestamp}
                        </div>
                      </div>
                    </div>
                  )
                }

                return (
                  <div key={message.id} className="flex items-start gap-3.5">
                    <div className="mt-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-violet text-white shadow-sm dark:from-blue-600 dark:to-purple-600">
                      <Sparkles size={16} />
                    </div>

                    <div className="min-w-0 flex-1 space-y-3">
                      <GlassCard className="rounded-3xl rounded-tl-sm p-6 shadow-sm dark:bg-[#10182c] dark:border-white/15">
                        {/* Scope & Evidence Header */}
                        {message.evidenceState && (
                          <div className="mb-4 flex flex-wrap items-center justify-between gap-2 border-b border-border/60 dark:border-white/10 pb-3">
                            <div className="flex items-center gap-2">
                              <Badge
                                tone={
                                  message.evidenceState === 'Strong'
                                    ? 'teal'
                                    : message.evidenceState === 'Moderate'
                                    ? 'primary'
                                    : 'amber'
                                }
                              >
                                {message.evidenceState} Evidence
                              </Badge>
                              {message.targetPaperTitle && (
                                <Badge tone="neutral" className="max-w-[260px] truncate text-[10px]">
                                  📄 {message.targetPaperTitle}
                                </Badge>
                              )}
                              {message.knowledgeScope && (
                                <span className="text-[10px] text-slate dark:text-slate-300 font-medium">
                                  Scope: {message.knowledgeScope}
                                </span>
                              )}
                            </div>

                            <div className="flex items-center gap-2.5">
                              {/* XAI Explain Button in Header */}
                              {(message.structuredCitations?.length || message.xaiExplanation) && (
                                <button
                                  type="button"
                                  onClick={() => setSelectedXaiModalMessage(message)}
                                  className="inline-flex items-center gap-1.5 rounded-full border border-teal/40 bg-teal-soft/70 px-2.5 py-1 text-[11px] font-bold text-teal transition hover:border-teal hover:bg-teal-soft dark:bg-emerald-950/40 dark:border-emerald-500/40 dark:text-emerald-300 dark:hover:bg-emerald-900/40 shadow-xs cursor-pointer"
                                  title="Inspect transparent scores, claim grounding checks, and funnel filtration"
                                >
                                  <ShieldCheck size={12} className="text-teal dark:text-emerald-400" />
                                  <span>Explain (XAI)</span>
                                  {message.faithfulnessScore !== undefined && message.faithfulnessScore !== null && (
                                    <span className="rounded-full bg-teal/20 px-1.5 py-0.2 text-[9px] font-extrabold">
                                      {message.faithfulnessScore.toFixed(0)}%
                                    </span>
                                  )}
                                </button>
                              )}

                              {message.latencyMs ? (
                                <span className="flex items-center gap-1 text-[10px] font-mono text-slate dark:text-slate-400">
                                  <Clock size={11} /> {(message.latencyMs / 1000).toFixed(2)}s
                                </span>
                              ) : null}
                            </div>
                          </div>
                        )}

                        {/* Markdown Formatted Answer */}
                        <div className="prose prose-sm max-w-none text-sm leading-relaxed text-ink dark:text-slate-100">
                          <ReactMarkdown>{message.content}</ReactMarkdown>
                        </div>

                        {/* Interactive Citation Pills & Grounding Sources (Only when evidence is valid and not abstained) */}
                        {(() => {
                          const isAbstaining =
                            message.abstained ||
                            message.evidenceState === 'insufficient' ||
                            message.content?.toLowerCase().includes("couldn't find sufficient evidence") ||
                            message.content?.toLowerCase().includes("no supporting research documents")

                          if (isAbstaining) return null

                          return (
                            <>
                              {message.structuredCitations && message.structuredCitations.length > 0 && (
                                <div className="mt-5 pt-4 border-t border-border/80 dark:border-white/10">
                                  <div className="mb-2 flex items-center justify-between">
                                    <p className="mono-label text-[10px] text-slate dark:text-slate-300 font-semibold flex items-center gap-1">
                                      <Bookmark size={12} className="text-violet dark:text-purple-400" /> Verified Inline Citations:
                                    </p>
                                    <span className="text-[10px] text-slate dark:text-slate-400">
                                      Click title to open PDF · Click score for XAI rationale
                                    </span>
                                  </div>

                                  <div className="flex flex-wrap gap-2">
                                    {message.structuredCitations.map((cit) => (
                                      <div
                                        key={cit.citation_id}
                                        className="group inline-flex items-center gap-1.5 rounded-full border border-violet/30 bg-violet-soft/60 py-1 pl-3 pr-1.5 text-xs font-semibold text-violet transition hover:border-violet dark:bg-purple-950/40 dark:border-purple-500/40 dark:text-purple-300 shadow-xs"
                                      >
                                        <button
                                          onClick={() => handleCitationClick(cit)}
                                          className="inline-flex items-center gap-1.5 hover:underline"
                                          title={`Open ${cit.title} at page ${cit.page_start}`}
                                        >
                                          <span className="font-bold">[{cit.citation_id}]</span>
                                          <span className="max-w-[160px] truncate text-[11px] font-normal text-ink dark:text-white">
                                            {cit.title}
                                          </span>
                                          <span className="text-[10px] text-slate dark:text-slate-400">
                                            p.{cit.page_start}
                                          </span>
                                          <ExternalLink size={11} className="opacity-70 group-hover:opacity-100" />
                                        </button>

                                        <button
                                          type="button"
                                          onClick={(e) => {
                                            e.stopPropagation()
                                            setInspectingCitation(cit)
                                          }}
                                          className="ml-1 inline-flex items-center gap-1 rounded-full bg-surface px-2 py-0.5 text-[10px] font-bold text-violet border border-violet/20 hover:border-violet hover:bg-violet-soft dark:bg-purple-900/60 dark:text-purple-200 dark:border-purple-400/30 dark:hover:bg-purple-800 transition cursor-pointer"
                                          title="Click to see why this particular citation was chosen and its 4-stage score breakdown"
                                        >
                                          <BarChart3 size={11} />
                                          <span>
                                            {cit.score_breakdown?.final_confidence
                                              ? `${cit.score_breakdown.final_confidence}%`
                                              : 'Why Chosen'}
                                          </span>
                                        </button>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}

                              {message.sources && message.sources.length > 0 && (
                                <div className="mt-4 space-y-2">
                                  <details className="group">
                                    <summary className="cursor-pointer text-xs font-semibold text-slate hover:text-primary dark:text-slate-300 dark:hover:text-blue-300 transition flex items-center gap-1.5 list-none">
                                      <span className="mono-label text-[10px] text-primary dark:text-blue-400">
                                        ▶ View Grounding Evidence Chunks ({message.sources.length})
                                      </span>
                                    </summary>
                                    <div className="mt-3 space-y-2.5 pt-2">
                                      {message.sources.map((src, sIdx) => (
                                        <div
                                          key={src.chunk_id || sIdx}
                                          className="rounded-2xl border border-border bg-surface-muted/60 p-3.5 text-xs dark:bg-white/5 dark:border-white/10"
                                        >
                                          <div className="flex items-start justify-between gap-2">
                                            <div className="min-w-0">
                                              <p className="font-bold text-ink truncate dark:text-white">{src.title}</p>
                                              <p className="text-[11px] text-slate dark:text-slate-300 mt-0.5">
                                                Section: {src.section} · Page {src.page_start}
                                              </p>
                                            </div>
                                            <button
                                              onClick={() =>
                                                openPdfViewer({
                                                  paperId: src.paper_id,
                                                  title: src.title,
                                                  page: src.page_start,
                                                  snippet: src.text,
                                                  section: src.section,
                                                })
                                              }
                                              className="shrink-0 text-xs font-semibold text-primary hover:underline flex items-center gap-1 dark:text-blue-400"
                                            >
                                              Inspect PDF <ExternalLink size={11} />
                                            </button>
                                          </div>
                                          <p className="mt-2 line-clamp-3 text-[11px] leading-relaxed text-slate italic bg-surface p-2 rounded-xl border border-border/50 dark:bg-white/5 dark:text-slate-200 dark:border-white/10">
                                            "{src.text}"
                                          </p>
                                        </div>
                                      ))}
                                    </div>
                                  </details>
                                </div>
                              )}
                            </>
                          )
                        })()}
                      </GlassCard>

                      <div className="flex items-center gap-2 pl-2">
                        <CopyButton value={message.content} />
                        {(message.structuredCitations?.length || message.xaiExplanation) && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setSelectedXaiModalMessage(message)}
                            className="text-xs text-teal hover:text-teal hover:bg-teal-soft/60 dark:text-emerald-300 dark:hover:bg-emerald-950/40 gap-1.5 h-8"
                          >
                            <ShieldCheck size={13} />
                            <span>Explain Answer (XAI)</span>
                          </Button>
                        )}
                        <span className="text-[10px] text-slate">{message.timestamp}</span>
                      </div>
                    </div>
                  </div>
                )
              })}

              {/* In-Flight Gemini Loading Indicator */}
              {isLoading && (
                <div className="flex items-start gap-3.5">
                  <div className="mt-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-violet text-white shadow-sm">
                    <Sparkles size={16} />
                  </div>
                  <GlassCard className="min-w-0 flex-1 rounded-3xl rounded-tl-sm p-6">
                    <div className="flex items-center gap-3">
                      <LoaderCircle size={18} className="animate-spin text-primary" />
                      <div>
                        <p className="font-display text-base font-semibold text-ink">
                          Synthesizing research evidence...
                        </p>
                        <p className="mt-0.5 text-xs text-slate">
                          Executing hybrid dense-lexical retrieval, cross-encoder reranking, and Gemini grounding.
                        </p>
                      </div>
                    </div>
                  </GlassCard>
                </div>
              )}

              {/* Insufficient Evidence & Online Discovery Banner (Required by Section 6) */}
              {activeSufficiencyAlert && (
                <div className="rounded-3xl border border-amber/40 bg-amber-soft/80 p-5 shadow-lg backdrop-blur dark:bg-amber-950/20">
                  <div className="flex items-start gap-3.5">
                    <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-2xl bg-amber text-white">
                      <AlertCircle size={18} />
                    </div>
                    <div className="flex-1">
                      <h4 className="font-display text-base font-bold text-ink">
                        Insufficient Evidence in Selected Sources
                      </h4>
                      <p className="mt-1 text-xs leading-relaxed text-slate font-medium">
                        I couldn't find sufficient evidence in the selected research sources.
                        Would you like to search online research papers across arXiv and Semantic Scholar?
                      </p>

                      <div className="mt-4 flex flex-wrap items-center gap-3">
                        <Button
                          variant="primary"
                          size="sm"
                          onClick={handleStartOnlineSearch}
                          className="bg-amber hover:bg-amber/90 text-white"
                        >
                          <Search size={14} /> Search Online
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setActiveSufficiencyAlert(null)}
                        >
                          Cancel
                        </Button>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          </div>

          {/* Bottom Query Input Box */}
          <div className="border-t border-border bg-canvas/85 p-4 backdrop-blur-xl sm:p-6">
            <div className="mx-auto max-w-3xl space-y-3">
              {/* Scope Selector Bar */}
              <div className="flex flex-wrap items-center justify-between gap-2 px-1">
                <div className="flex items-center gap-2">
                  <span className="mono-label text-[10px] text-slate font-bold">SOURCE SCOPE:</span>
                  <ScopeSelector />
                </div>
                <button
                  type="button"
                  onClick={() => openOnlineDiscovery()}
                  className="inline-flex items-center gap-1.5 text-xs font-semibold text-primary hover:underline"
                >
                  <Globe size={13} /> Online Discovery
                </button>
              </div>

              {/* Text Input Container */}
              <GlassCard className="rounded-3xl p-2.5 ring-4 ring-primary/5 shadow-md dark:bg-[#10182c] dark:border-white/15 dark:ring-blue-500/10">
                <div className="flex items-end gap-2">
                  <textarea
                    rows={2}
                    value={draft}
                    onChange={(e) => setDraft(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault()
                        handleSend()
                      }
                    }}
                    placeholder={`Ask a research question in ${currentScopeOpt.shortLabel}... (e.g. Compare FlashAttention vs standard attention)`}
                    className="max-h-36 min-h-12 flex-1 resize-none bg-transparent px-3 py-2 text-sm text-ink outline-none placeholder:text-slate/60 dark:text-white dark:placeholder:text-slate-400"
                  />
                  <button
                    onClick={() => handleSend()}
                    disabled={!draft.trim() || isLoading}
                    className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-violet text-white shadow-sm transition hover:scale-105 disabled:opacity-40 disabled:hover:scale-100 dark:from-blue-600 dark:to-purple-600"
                    aria-label="Send research query"
                  >
                    {isLoading ? (
                      <LoaderCircle size={18} className="animate-spin" />
                    ) : (
                      <Send size={18} />
                    )}
                  </button>
                </div>
              </GlassCard>

              {/* Sample Queries */}
              <div className="flex flex-wrap justify-center gap-1.5 pt-1">
                {DEFAULT_QUESTIONS.slice(0, 3).map((q) => (
                  <button
                    key={q}
                    onClick={() => handleSend(q)}
                    className="rounded-full border border-border bg-surface px-3 py-1.5 text-[10px] font-semibold text-slate transition hover:border-primary/40 hover:text-primary dark:bg-white/5 dark:text-slate-300 dark:border-white/10 dark:hover:text-blue-300 dark:hover:border-blue-500/40"
                  >
                    {q}
                  </button>
                ))}
              </div>

              <p className="text-center text-[10px] text-slate/70 dark:text-slate-400">
                Lumina strictly anchors answers to retrieved peer-reviewed chunks. Verify critical conclusions via inline citations.
              </p>
            </div>
          </div>
        </div>

        {/* Right Sidebar: Active Research Context & Provenance */}
        <aside className="hidden border-l border-border bg-surface-muted/40 p-6 xl:block overflow-y-auto">
          <div className="space-y-6">
            <div>
              <p className="mono-label text-slate">Active Scope Configuration</p>
              <div className="mt-3 rounded-2xl border border-border bg-surface p-4 shadow-sm dark:bg-white/5">
                <div className="flex items-center gap-2">
                  <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-primary-soft text-primary">
                    <Layers size={16} />
                  </div>
                  <div className="min-w-0">
                    <p className="truncate text-xs font-bold text-ink">
                      {currentScopeOpt.label}
                    </p>
                    <p className="text-[10px] text-slate">{currentScopeOpt.shortLabel}</p>
                  </div>
                </div>
                <p className="mt-3 text-[11px] leading-relaxed text-slate">
                  {currentScopeOpt.description}
                </p>

                {selectedScope === 'this_paper' && selectedPaperTitle && (
                  <div className="mt-3 rounded-xl border border-violet/20 bg-violet-soft/30 p-2.5">
                    <p className="text-[9px] font-bold uppercase tracking-wider text-violet">
                      Target Document
                    </p>
                    <p className="text-xs font-semibold text-ink truncate mt-0.5">
                      {selectedPaperTitle}
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Retrieval Telemetry */}
            <div>
              <p className="mono-label text-slate">Query Telemetry</p>
              <div className="mt-3 grid grid-cols-2 gap-2">
                <div className="rounded-2xl border border-border bg-surface p-3 text-center dark:bg-white/5">
                  <p className="font-display text-2xl font-bold text-primary">
                    {latestAssistant?.latencyMs
                      ? `${(latestAssistant.latencyMs / 1000).toFixed(2)}s`
                      : '0.0s'}
                  </p>
                  <p className="text-[10px] text-slate">Retrieval & LLM</p>
                </div>
                <div className="rounded-2xl border border-border bg-surface p-3 text-center dark:bg-white/5">
                  <p className="font-display text-2xl font-bold text-teal">
                    {latestAssistant?.structuredCitations?.length ?? 0}
                  </p>
                  <p className="text-[10px] text-slate">Citations Verified</p>
                </div>
              </div>
            </div>

            {/* Explainable AI (XAI) Sidebar Card */}
            {latestAssistant && latestAssistant.role === 'assistant' && (
              <div className="rounded-2xl border border-teal/30 bg-teal-soft/30 p-4 dark:bg-emerald-950/20 dark:border-emerald-500/30 space-y-2.5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5 font-bold text-xs text-teal dark:text-emerald-300">
                    <ShieldCheck size={16} />
                    <span>Explainable AI (XAI)</span>
                  </div>
                  <span className="rounded-full bg-teal/20 px-2 py-0.5 text-[10px] font-extrabold text-teal dark:text-emerald-300">
                    {latestAssistant.faithfulnessScore !== undefined && latestAssistant.faithfulnessScore !== null
                      ? `${latestAssistant.faithfulnessScore.toFixed(0)}% Grounded`
                      : 'Verified'}
                  </span>
                </div>
                <p className="text-[11px] text-slate dark:text-slate-300 leading-relaxed">
                  Transparent 4-stage retrieval audit with Cross-Encoder scores and verified claims.
                </p>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => setSelectedXaiModalMessage(latestAssistant)}
                  className="w-full text-xs gap-1.5 h-8 bg-teal hover:bg-teal/90 text-white"
                >
                  <BarChart3 size={13} />
                  <span>Inspect Full XAI Audit</span>
                </Button>
              </div>
            )}

            {/* Referenced Papers in Current Turn */}
            <div>
              <p className="mono-label text-slate">Referenced in Last Response</p>
              <div className="mt-3 space-y-2">
                {latestAssistant?.structuredCitations &&
                latestAssistant.structuredCitations.length > 0 ? (
                  latestAssistant.structuredCitations.map((cit) => (
                    <button
                      key={cit.citation_id}
                      onClick={() => handleCitationClick(cit)}
                      className="group flex w-full items-start gap-2.5 rounded-xl border border-border bg-surface p-3 text-left transition hover:border-primary/40 hover:bg-primary-soft/30 dark:bg-white/5"
                    >
                      <FileText size={15} className="mt-0.5 shrink-0 text-violet" />
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-xs font-bold text-ink group-hover:text-primary">
                          [{cit.citation_id}] {cit.title}
                        </p>
                        <p className="text-[10px] text-slate mt-0.5">
                          Section: {cit.section} · Page {cit.page_start}
                        </p>
                      </div>
                    </button>
                  ))
                ) : (
                  <p className="text-xs text-slate italic p-3 rounded-xl border border-dashed border-border text-center">
                    Ask a question to see grounded paper references.
                  </p>
                )}
              </div>
            </div>

            {/* Knowledge Base Overview */}
            <div className="rounded-2xl border border-border bg-surface p-4 text-xs dark:bg-white/5">
              <div className="flex items-center gap-2 font-semibold text-ink">
                <CheckCircle2 size={15} className="text-teal" />
                <span>FAISS & BM25 Active</span>
              </div>
              <p className="mt-2 text-[11px] text-slate leading-relaxed">
                Indexed repository contains{' '}
                <strong className="text-ink font-semibold">{papers.length} papers</strong> ready for
                semantic search and question answering.
              </p>
            </div>
          </div>
        </aside>
      </div>

      {/* Interactive XAI Modals */}
      <CitationInspectorModal
        citation={inspectingCitation}
        isOpen={!!inspectingCitation}
        onClose={() => setInspectingCitation(null)}
        onOpenPdf={handleCitationClick}
      />

      <XaiAuditModal
        isOpen={!!selectedXaiModalMessage}
        onClose={() => setSelectedXaiModalMessage(null)}
        query={selectedXaiModalMessage?.content || ''}
        answer={selectedXaiModalMessage?.content || ''}
        faithfulnessScore={selectedXaiModalMessage?.faithfulnessScore}
        xaiExplanation={selectedXaiModalMessage?.xaiExplanation}
        componentAssessment={selectedXaiModalMessage?.componentAssessment}
        structuredCitations={selectedXaiModalMessage?.structuredCitations}
        targetPaperTitle={selectedXaiModalMessage?.targetPaperTitle}
        onOpenPdf={handleCitationClick}
        onInspectCitation={(cit) => {
          setSelectedXaiModalMessage(null)
          setInspectingCitation(cit)
        }}
      />
    </div>
  )
}
