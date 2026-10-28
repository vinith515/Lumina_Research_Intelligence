import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { ArrowLeft, ArrowRight, Eye, EyeOff, LockKeyhole, Mail, Sparkles, User } from 'lucide-react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { Button, Field, GlassCard, Input } from '../components/ui/Primitives'
import { useAuth } from '../context/AuthContext'

type AuthMode = 'login' | 'signup' | 'forgot' | 'reset'
interface AuthForm {
  name?: string
  email: string
  password?: string
  institution?: string
}

const copy: Record<AuthMode, { eyebrow: string; title: string; description: string; submit: string }> = {
  login: {
    eyebrow: 'Welcome back',
    title: 'Access your research workspace.',
    description: 'Continue your literature analysis with dynamic, grounded citations.',
    submit: 'Sign in to Lumina',
  },
  signup: {
    eyebrow: 'Get started',
    title: 'Build your research intelligence workspace.',
    description: 'Create a private, citation-grounded research workspace in seconds.',
    submit: 'Create workspace',
  },
  forgot: {
    eyebrow: 'Account recovery',
    title: 'Find your way back in.',
    description: 'We will send a secure password reset link to your email.',
    submit: 'Send reset link',
  },
  reset: {
    eyebrow: 'New credentials',
    title: 'Choose a strong password.',
    description: 'Choose a new password for your Lumina workspace.',
    submit: 'Save new password',
  },
}

function resolveMode(pathname: string): AuthMode {
  if (pathname.includes('signup')) return 'signup'
  if (pathname.includes('forgot')) return 'forgot'
  if (pathname.includes('reset')) return 'reset'
  return 'login'
}

export function AuthPage() {
  const mode = resolveMode(useLocation().pathname)
  const navigate = useNavigate()
  const { login, signup } = useAuth()
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<AuthForm>({ mode: 'onBlur' })
  const [showPassword, setShowPassword] = useState(false)
  const isPassword = mode === 'login' || mode === 'signup' || mode === 'reset'
  const isSignup = mode === 'signup'

  const onSubmit = async (data: AuthForm) => {
    await new Promise((resolve) => setTimeout(resolve, 400))
    if (mode === 'forgot') {
      toast.success('Reset link sent. Check your inbox.')
      return
    }
    if (mode === 'reset') {
      toast.success('Password updated.')
      navigate('/login')
      return
    }

    if (isSignup) {
      signup(data.name || '', data.email, data.password, data.institution)
      toast.success(`Welcome to Lumina, ${data.name || 'Researcher'}!`)
    } else {
      login(data.email, data.password, data.name, data.institution)
      toast.success('Welcome back to Lumina.')
    }
    navigate('/app')
  }

  return (
    <div className="min-h-screen bg-canvas text-ink">
      <div className="grid min-h-screen lg:grid-cols-[0.92fr_1.08fr]">
        <section className="relative hidden overflow-hidden bg-[#0e1730] p-10 text-white lg:flex lg:flex-col lg:justify-between">
          <div className="absolute -right-20 top-24 h-96 w-96 rounded-full bg-primary/50 blur-3xl" />
          <div className="absolute -bottom-20 -left-20 h-80 w-80 rounded-full bg-violet/50 blur-3xl" />
          <Link to="/" className="relative flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-white/10">
              <Sparkles size={18} />
            </span>
            <span className="font-display text-3xl font-semibold">Lumina</span>
          </Link>
          <div className="relative max-w-lg">
            <p className="mono-label mb-5 text-[#86a8ff]">Grounded Scientific RAG Platform</p>
            <h1 className="font-display text-7xl font-semibold leading-[0.87] tracking-[-0.04em]">
              Make scientific literature verifiable.
            </h1>
            <p className="mt-7 max-w-md text-sm leading-6 text-white/60">
              Dual-index hybrid search, strict claim verification, and spatial PDF bounding boxes for rigorous research synthesis.
            </p>
            <div className="mt-12 grid max-w-md grid-cols-3 gap-2">
              <div className="rounded-2xl border border-white/10 bg-white/5 p-3">
                <p className="font-display text-3xl">316+</p>
                <p className="mt-1 text-[10px] text-white/45">peer-reviewed papers</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-3">
                <p className="font-display text-3xl">48.6k</p>
                <p className="mt-1 text-[10px] text-white/45">indexed chunks</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-3">
                <p className="font-display text-3xl">100%</p>
                <p className="mt-1 text-[10px] text-white/45">verifiable citations</p>
              </div>
            </div>
          </div>
          <p className="relative text-xs text-white/35">Private by design · SciBERT & Cross-Encoder Reranking</p>
        </section>

        <section className="flex min-h-screen items-center justify-center px-5 py-10 sm:px-8">
          <div className="w-full max-w-md">
            <div className="mb-8 flex items-center justify-between lg:hidden">
              <Link to="/" className="flex items-center gap-2">
                <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-ink text-white">
                  <Sparkles size={16} />
                </span>
                <span className="font-display text-2xl font-semibold">Lumina</span>
              </Link>
              <Link to="/" className="text-xs text-slate">
                Back to home
              </Link>
            </div>

            <GlassCard className="p-6 sm:p-8">
              <Link
                to="/"
                className="mb-8 hidden items-center gap-2 text-xs text-slate hover:text-primary lg:inline-flex"
              >
                <ArrowLeft size={14} /> Back to home
              </Link>
              <p className="mono-label mb-3 text-primary">{copy[mode].eyebrow}</p>
              <h2 className="font-display text-5xl font-semibold leading-[0.92] text-ink">{copy[mode].title}</h2>
              <p className="mt-4 text-sm leading-6 text-slate">{copy[mode].description}</p>

              <form className="mt-8 space-y-5" onSubmit={handleSubmit(onSubmit)}>
                {isSignup && (
                  <Field label="Full name" error={errors.name?.message}>
                    <div className="relative">
                      <User size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate" />
                      <Input
                        className="pl-10"
                        placeholder="Alex Morgan"
                        {...register('name', { required: 'Your name is required.' })}
                      />
                    </div>
                  </Field>
                )}

                <Field label="Research email" error={errors.email?.message}>
                  <div className="relative">
                    <Mail size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate" />
                    <Input
                      className="pl-10"
                      type="email"
                      placeholder="researcher@university.edu"
                      {...register('email', {
                        required: 'Email is required.',
                        pattern: { value: /\S+@\S+\.\S+/, message: 'Enter a valid email address.' },
                      })}
                    />
                  </div>
                </Field>

                {isSignup && (
                  <Field label="Institution / Organization" hint="Helps tailor your research context.">
                    <Input placeholder="Department of Computer Science" {...register('institution')} />
                  </Field>
                )}

                {isPassword && (
                  <Field label="Password" error={errors.password?.message}>
                    <div className="relative">
                      <LockKeyhole size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate" />
                      <Input
                        className="pl-10 pr-11"
                        type={showPassword ? 'text' : 'password'}
                        placeholder={mode === 'reset' ? 'Choose a new password' : 'Enter your password'}
                        {...register('password', {
                          required: 'Password is required.',
                          minLength: { value: 6, message: 'Use at least 6 characters.' },
                        })}
                      />
                      <button
                        type="button"
                        className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate"
                        onClick={() => setShowPassword((value) => !value)}
                        aria-label="Toggle password visibility"
                      >
                        {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                      </button>
                    </div>
                  </Field>
                )}

                {mode === 'login' && (
                  <div className="flex justify-end">
                    <Link to="/forgot-password" className="text-xs font-semibold text-primary hover:underline">
                      Forgot password?
                    </Link>
                  </div>
                )}

                <Button type="submit" variant="primary" size="lg" className="w-full" disabled={isSubmitting}>
                  {isSubmitting ? 'Authenticating…' : copy[mode].submit}{' '}
                  {!isSubmitting && <ArrowRight size={16} />}
                </Button>
              </form>

              <div className="mt-7 border-t border-border pt-6 text-center text-xs text-slate">
                {mode === 'login' ? (
                  <>
                    New to Lumina?{' '}
                    <Link to="/signup" className="font-bold text-primary">
                      Create an account
                    </Link>
                  </>
                ) : mode === 'signup' ? (
                  <>
                    Already have an account?{' '}
                    <Link to="/login" className="font-bold text-primary">
                      Sign in
                    </Link>
                  </>
                ) : (
                  <Link to="/login" className="font-bold text-primary">
                    Return to sign in
                  </Link>
                )}
              </div>
            </GlassCard>
          </div>
        </section>
      </div>
    </div>
  )
}
