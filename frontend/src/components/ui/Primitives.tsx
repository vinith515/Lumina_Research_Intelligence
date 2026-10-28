import { forwardRef, type ButtonHTMLAttributes, type InputHTMLAttributes, type ReactNode, type TextareaHTMLAttributes } from 'react'
import { ArrowRight, Check, ChevronLeft, ChevronRight, Copy, X } from 'lucide-react'

export function cn(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(' ')
}

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger' | 'dark'
  size?: 'sm' | 'md' | 'lg' | 'icon'
  children: ReactNode
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button({ className, variant = 'secondary', size = 'md', children, ...props }, ref) {
  const variants = {
    primary: 'gradient-button hover:-translate-y-0.5 hover:shadow-[0_16px_28px_rgba(53,0,133,0.25)] text-white',
    secondary: 'border border-border bg-surface text-ink hover:border-primary/30 hover:bg-primary-soft/60 dark:bg-surface dark:text-white dark:border-white/15 dark:hover:bg-white/10',
    ghost: 'text-slate hover:bg-primary-soft/60 hover:text-primary dark:text-slate-200 dark:hover:bg-white/10 dark:hover:text-white',
    danger: 'border border-danger/20 bg-danger-soft text-danger hover:bg-danger/10 dark:border-red-500/30 dark:bg-red-500/20 dark:text-red-300',
    dark: 'bg-ink text-white hover:bg-primary dark:bg-white dark:text-ink dark:hover:bg-slate-200',
  }
  const sizes = { sm: 'h-9 px-3 text-xs', md: 'h-11 px-4 text-sm', lg: 'h-13 px-6 text-sm', icon: 'h-10 w-10 p-0' }
  return <button ref={ref} className={cn('inline-flex items-center justify-center gap-2 rounded-full font-semibold transition-all duration-200 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary disabled:cursor-not-allowed disabled:opacity-50', variants[variant], sizes[size], className)} {...props}>{children}</button>
})

export function GlassCard({ children, className, interactive = false }: { children: ReactNode; className?: string; interactive?: boolean }) {
  return <div className={cn('glass-panel rounded-card', interactive && 'transition-all duration-200 hover:-translate-y-1 hover:shadow-float', className)}>{children}</div>
}

export function SectionHeader({ eyebrow, title, description, action }: { eyebrow?: string; title: string; description?: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <p className="mono-label mb-2 text-primary dark:text-primary-soft">{eyebrow}</p>
        <h1 className="font-display text-4xl font-semibold leading-[0.98] tracking-tight text-ink sm:text-5xl">{title}</h1>
        {description && <p className="mt-3 max-w-2xl text-sm leading-6 text-slate dark:text-slate-300">{description}</p>}
      </div>
      {action}
    </div>
  )
}

export function Badge({ children, tone = 'neutral', className }: { children: ReactNode; tone?: 'neutral' | 'primary' | 'violet' | 'teal' | 'amber' | 'danger'; className?: string }) {
  const tones = {
    neutral: 'bg-surface-muted text-slate dark:bg-white/10 dark:text-slate-200',
    primary: 'bg-primary-soft text-primary dark:bg-blue-900/40 dark:text-blue-300 dark:border dark:border-blue-500/30',
    violet: 'bg-violet-soft text-violet dark:bg-purple-900/40 dark:text-purple-300 dark:border dark:border-purple-500/30',
    teal: 'bg-teal-soft text-teal dark:bg-teal-900/40 dark:text-teal-300 dark:border dark:border-teal-500/30',
    amber: 'bg-amber-soft text-amber dark:bg-amber-900/40 dark:text-amber-300 dark:border dark:border-amber-500/30',
    danger: 'bg-danger-soft text-danger dark:bg-red-900/40 dark:text-red-300 dark:border dark:border-red-500/30',
  }
  return <span className={cn('inline-flex items-center rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.12em]', tones[tone], className)}>{children}</span>
}

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(function Input({ className, ...props }, ref) {
  return <input ref={ref} className={cn('h-11 w-full rounded-xl border border-border bg-surface px-3.5 text-sm text-ink outline-none transition focus:border-primary/40 focus:ring-4 focus:ring-primary/10 placeholder:text-slate/60 dark:bg-[#131c35] dark:text-white dark:border-white/15 dark:placeholder:text-slate-400 focus:dark:border-primary', className)} {...props} />
})

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(function Textarea({ className, ...props }, ref) {
  return <textarea ref={ref} className={cn('w-full resize-none rounded-2xl border border-border bg-surface px-4 py-3 text-sm text-ink outline-none transition focus:border-primary/40 focus:ring-4 focus:ring-primary/10 placeholder:text-slate/60 dark:bg-[#131c35] dark:text-white dark:border-white/15 dark:placeholder:text-slate-400 focus:dark:border-primary', className)} {...props} />
})

export function Field({ label, hint, error, children }: { label: string; hint?: string; error?: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-semibold text-ink dark:text-slate-200">{label}</span>
      {children}
      {error ? <span className="mt-1.5 block text-xs text-danger dark:text-red-400">{error}</span> : hint ? <span className="mt-1.5 block text-xs text-slate dark:text-slate-400">{hint}</span> : null}
    </label>
  )
}

export function EmptyState({ icon, title, description, action }: { icon: ReactNode; title: string; description: string; action?: ReactNode }) {
  return <div className="glass-panel flex flex-col items-center justify-center rounded-card px-6 py-16 text-center"><div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-primary-soft text-primary dark:bg-white/10 dark:text-white">{icon}</div><h3 className="font-display text-3xl font-semibold text-ink">{title}</h3><p className="mt-2 max-w-sm text-sm leading-6 text-slate dark:text-slate-300">{description}</p>{action && <div className="mt-6">{action}</div>}</div>
}

export function StatCard({ label, value, change, icon, tone = 'primary' }: { label: string; value: string; change: string; icon: ReactNode; tone?: 'primary' | 'violet' | 'teal' | 'amber' }) {
  const tones = { 
    primary: 'bg-primary-soft text-primary dark:bg-blue-900/40 dark:text-blue-300', 
    violet: 'bg-violet-soft text-violet dark:bg-purple-900/40 dark:text-purple-300', 
    teal: 'bg-teal-soft text-teal dark:bg-teal-900/40 dark:text-teal-300', 
    amber: 'bg-amber-soft text-amber dark:bg-amber-900/40 dark:text-amber-300' 
  }
  return <GlassCard className="p-5"><div className="flex items-start justify-between"><div><p className="mono-label text-slate dark:text-slate-400">{label}</p><p className="mt-3 font-display text-4xl font-semibold text-ink">{value}</p></div><div className={cn('flex h-10 w-10 items-center justify-center rounded-xl', tones[tone])}>{icon}</div></div><p className="mt-4 text-xs font-semibold text-teal dark:text-teal-400">{change}</p></GlassCard>
}

export function Modal({ title, children, onClose }: { title: string; children: ReactNode; onClose: () => void }) {
  return <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm"><div className="glass-panel max-h-[90vh] w-full max-w-lg overflow-auto rounded-3xl bg-surface p-6 shadow-2xl dark:bg-[#10182c] border border-border dark:border-white/15"><div className="mb-5 flex items-center justify-between"><h2 className="font-display text-3xl font-semibold text-ink">{title}</h2><Button variant="ghost" size="icon" onClick={onClose} aria-label="Close dialog"><X size={18} /></Button></div>{children}</div></div>
}

export function Pagination({ page, totalPages, onChange }: { page: number; totalPages: number; onChange: (next: number) => void }) {
  return <div className="flex items-center justify-between gap-3 border-t border-border pt-5"><p className="text-xs text-slate dark:text-slate-300">Page {page} of {totalPages}</p><div className="flex items-center gap-1.5"><Button variant="ghost" size="icon" disabled={page === 1} onClick={() => onChange(page - 1)} aria-label="Previous page"><ChevronLeft size={16} /></Button>{Array.from({ length: totalPages }, (_, index) => index + 1).map((item) => <button key={item} className={cn('h-9 w-9 rounded-full text-xs font-bold transition', item === page ? 'bg-primary text-white' : 'text-slate hover:bg-primary-soft hover:text-primary dark:text-slate-300 dark:hover:bg-white/10 dark:hover:text-white')} onClick={() => onChange(item)}>{item}</button>)}<Button variant="ghost" size="icon" disabled={page === totalPages} onClick={() => onChange(page + 1)} aria-label="Next page"><ChevronRight size={16} /></Button></div></div>
}

export function CopyButton({ value }: { value: string }) {
  const copy = async () => { await navigator.clipboard?.writeText(value); }
  return <Button variant="ghost" size="icon" onClick={copy} aria-label="Copy to clipboard"><Copy size={15} /></Button>
}

export function Toggle({ checked, onChange, label }: { checked: boolean; onChange: (checked: boolean) => void; label: string }) {
  return <button type="button" role="switch" aria-checked={checked} aria-label={label} onClick={() => onChange(!checked)} className={cn('relative h-6 w-11 rounded-full transition', checked ? 'bg-primary' : 'bg-slate/25 dark:bg-white/20')}><span className={cn('absolute top-1 h-4 w-4 rounded-full bg-white shadow-sm transition-transform', checked ? 'translate-x-6' : 'translate-x-1')} /></button>
}

export function FeatureArrow() { return <ArrowRight size={16} aria-hidden="true" /> }
export function CheckIcon() { return <Check size={16} aria-hidden="true" /> }
