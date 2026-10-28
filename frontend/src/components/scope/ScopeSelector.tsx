import React from 'react'
import {
  FileText,
  Files,
  BookOpen,
  Library,
  Globe,
  ChevronDown,
  Check,
} from 'lucide-react'
import { useResearch } from '../../context/ResearchContext'
import type { KnowledgeScope } from '../../services/api'
import { cn } from '../ui/Primitives'

interface ScopeOption {
  id: KnowledgeScope
  label: string
  shortLabel: string
  description: string
  icon: React.ComponentType<{ size?: number; className?: string }>
  badgeTone: 'primary' | 'violet' | 'teal' | 'amber' | 'neutral'
}

export const SCOPE_OPTIONS: ScopeOption[] = [
  {
    id: 'this_paper',
    label: 'This uploaded paper',
    shortLabel: 'This Paper',
    description: 'Strictly isolate retrieval to one selected research paper.',
    icon: FileText,
    badgeTone: 'violet',
  },
  {
    id: 'user_papers',
    label: 'My uploaded papers',
    shortLabel: 'My Uploads',
    description: 'Search across all papers uploaded in your current research session.',
    icon: Files,
    badgeTone: 'teal',
  },
  {
    id: 'global',
    label: 'ResearchMind baseline corpus',
    shortLabel: 'ResearchMind KB',
    description: '316 papers across 5 core domains (CV, Deep Learning, GenAI, ML, NLP).',
    icon: BookOpen,
    badgeTone: 'primary',
  },
  {
    id: 'global_plus_user',
    label: 'ResearchMind + my uploaded papers',
    shortLabel: 'KB + My Uploads',
    description: 'Synthesizes 5 core baseline domains with all your uploaded documents.',
    icon: Library,
    badgeTone: 'amber',
  },
  {
    id: 'global_plus_user_plus_online',
    label: 'Expanded research (online search with user approval)',
    shortLabel: 'Expanded Research',
    description: 'Full synthesis across baseline, custom uploads, and imported arXiv/S2 papers.',
    icon: Globe,
    badgeTone: 'violet',
  },
]

export function ScopeSelector() {
  const {
    selectedScope,
    setSelectedScope,
    selectedPaperId,
    setSelectedPaperId,
    selectedPaperTitle,
    setSelectedPaperTitle,
    papers,
  } = useResearch()

  const [isOpen, setIsOpen] = React.useState(false)
  const [isPaperPickerOpen, setIsPaperPickerOpen] = React.useState(false)

  const currentOption =
    SCOPE_OPTIONS.find((opt) => opt.id === selectedScope) || SCOPE_OPTIONS[2]
  const CurrentIcon = currentOption.icon

  // Uploaded / available papers for "This uploaded paper"
  const selectablePapers = papers.filter((p) => p.is_user_uploaded || p.scope !== 'global')
  const fallbackPapers = selectablePapers.length > 0 ? selectablePapers : papers

  function handleSelectScope(scopeId: KnowledgeScope) {
    setSelectedScope(scopeId)
    setIsOpen(false)
    if (scopeId === 'this_paper') {
      setIsPaperPickerOpen(true)
      // Pick first paper if none chosen
      if (!selectedPaperId && fallbackPapers.length > 0) {
        setSelectedPaperId(fallbackPapers[0].paper_id)
        setSelectedPaperTitle(fallbackPapers[0].title)
      }
    }
  }

  function handleSelectPaper(paperId: string, title: string) {
    setSelectedPaperId(paperId)
    setSelectedPaperTitle(title)
    setIsPaperPickerOpen(false)
  }

  return (
    <div className="relative inline-flex flex-wrap items-center gap-2">
      {/* Scope Trigger Button */}
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className="inline-flex items-center gap-2 rounded-full border border-border bg-surface px-3 py-1.5 text-xs font-semibold text-ink shadow-sm transition hover:border-primary/40 hover:bg-primary-soft/50 dark:bg-white/5"
      >
        <CurrentIcon size={14} className="text-primary" />
        <span className="truncate max-w-[200px]">{currentOption.shortLabel}</span>
        <ChevronDown size={13} className="text-slate" />
      </button>

      {/* Target Paper Picker (only visible when 'this_paper' is selected) */}
      {selectedScope === 'this_paper' && (
        <div className="relative">
          <button
            type="button"
            onClick={() => setIsPaperPickerOpen((prev) => !prev)}
            className="inline-flex max-w-[260px] items-center gap-1.5 rounded-full border border-violet/30 bg-violet-soft/50 px-3 py-1.5 text-xs font-bold text-violet transition hover:bg-violet-soft"
          >
            <FileText size={13} />
            <span className="truncate">
              {selectedPaperTitle || 'Choose paper...'}
            </span>
            <ChevronDown size={12} />
          </button>

          {isPaperPickerOpen && (
            <div className="absolute left-0 top-full z-40 mt-1 max-h-60 w-72 overflow-y-auto rounded-2xl border border-border bg-surface p-2 shadow-xl dark:bg-[#0f172a]">
              <div className="px-2 py-1.5 text-[10px] font-bold uppercase tracking-wider text-slate">
                Select Isolated Target Paper
              </div>
              {fallbackPapers.length === 0 ? (
                <p className="p-3 text-xs text-slate">
                  No papers available. Upload a paper first.
                </p>
              ) : (
                fallbackPapers.map((paper) => (
                  <button
                    key={paper.paper_id}
                    onClick={() => handleSelectPaper(paper.paper_id, paper.title)}
                    className={cn(
                      'flex w-full items-center justify-between rounded-xl px-2.5 py-2 text-left text-xs transition',
                      paper.paper_id === selectedPaperId
                        ? 'bg-primary-soft font-bold text-primary'
                        : 'text-ink hover:bg-surface-muted'
                    )}
                  >
                    <span className="truncate pr-2">{paper.title}</span>
                    {paper.paper_id === selectedPaperId && <Check size={14} />}
                  </button>
                ))
              )}
            </div>
          )}
        </div>
      )}

      {/* Dropdown Menu for Scopes */}
      {isOpen && (
        <>
          <div className="fixed inset-0 z-30" onClick={() => setIsOpen(false)} />
          <div className="absolute bottom-full left-0 z-40 mb-2 w-80 rounded-3xl border border-border bg-surface p-2 shadow-2xl dark:bg-[#0f172a]">
            <div className="px-3 py-2 text-[10px] font-bold uppercase tracking-widest text-slate">
              Retrieval Scope Isolation
            </div>
            <div className="space-y-1">
              {SCOPE_OPTIONS.map((opt) => {
                const isSelected = selectedScope === opt.id
                const Icon = opt.icon
                return (
                  <button
                    key={opt.id}
                    onClick={() => handleSelectScope(opt.id)}
                    className={cn(
                      'flex w-full items-start gap-3 rounded-2xl p-2.5 text-left transition',
                      isSelected
                        ? 'bg-primary-soft/80 text-primary dark:bg-primary/20'
                        : 'text-ink hover:bg-surface-muted/60'
                    )}
                  >
                    <div
                      className={cn(
                        'mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-xl',
                        isSelected ? 'bg-primary text-white' : 'bg-surface-muted text-slate'
                      )}
                    >
                      <Icon size={14} />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold leading-tight">{opt.label}</span>
                        {isSelected && <Check size={14} className="text-primary" />}
                      </div>
                      <p className="mt-0.5 text-[10px] text-slate leading-snug">
                        {opt.description}
                      </p>
                    </div>
                  </button>
                )
              })}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
