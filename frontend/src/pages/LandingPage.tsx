import { Link } from 'react-router-dom'

const features = [
  {
    icon: '🤖',
    title: 'AI-powered input',
    desc: 'Type "grabbed sushi for $32 last night" and Claude parses it into a structured transaction instantly.',
  },
  {
    icon: '📊',
    title: 'Visual dashboard',
    desc: 'Monthly income vs expenses, spending by category with bar, pie, and donut charts, and a full yearly overview.',
  },
  {
    icon: '🎯',
    title: 'Budget limits',
    desc: 'Set monthly limits per category. Watch progress bars turn amber at 75% and red when you go over.',
  },
  {
    icon: '💳',
    title: 'Full transaction history',
    desc: 'Add, edit, delete, and search all your transactions. Navigate any month or year.',
  },
  {
    icon: '⚡',
    title: 'Instant & private',
    desc: 'Your data lives in your own database. No third-party account linking, no data selling.',
  },
  {
    icon: '🔒',
    title: 'Secure by default',
    desc: 'JWT authentication, bcrypt-hashed passwords, and row-level ownership enforcement on every request.',
  },
]

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-white">
      {/* Nav */}
      <nav className="border-b border-slate-100">
        <div className="max-w-5xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-xl">💰</span>
            <span className="font-bold text-slate-900 text-base tracking-tight">BudgetAI</span>
          </div>
          <div className="flex items-center gap-2">
            <Link
              to="/login"
              className="px-4 py-1.5 text-sm font-medium text-slate-600 hover:text-slate-900 transition-colors"
            >
              Sign in
            </Link>
            <Link
              to="/register"
              className="px-4 py-1.5 text-sm font-medium bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
            >
              Get started
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-5xl mx-auto px-6 pt-20 pb-16 text-center">
        <div className="inline-flex items-center gap-2 px-3 py-1 bg-indigo-50 border border-indigo-100 rounded-full text-xs font-medium text-indigo-600 mb-6">
          <span>✨</span> Powered by Claude AI
        </div>
        <h1 className="text-5xl font-bold text-slate-900 tracking-tight leading-tight mb-5">
          Your finances,<br />
          <span className="text-indigo-600">finally under control</span>
        </h1>
        <p className="text-lg text-slate-500 max-w-xl mx-auto mb-8 leading-relaxed">
          Track income and expenses in plain English. BudgetAI parses your natural language
          into structured transactions, visualises your spending, and keeps you inside your limits.
        </p>
        <div className="flex items-center justify-center gap-3">
          <Link
            to="/register"
            className="px-6 py-2.5 bg-indigo-600 text-white text-sm font-semibold rounded-xl hover:bg-indigo-700 transition-colors shadow-sm"
          >
            Create free account
          </Link>
          <Link
            to="/login"
            className="px-6 py-2.5 border border-slate-300 text-slate-700 text-sm font-semibold rounded-xl hover:bg-slate-50 transition-colors"
          >
            Sign in
          </Link>
        </div>
      </section>

      {/* Demo callout */}
      <section className="max-w-5xl mx-auto px-6 pb-16">
        <div className="bg-slate-900 rounded-2xl p-6 text-center">
          <p className="text-slate-400 text-xs uppercase tracking-widest mb-3 font-medium">Natural language input</p>
          <div className="flex items-center justify-center gap-3 flex-wrap">
            {[
              '"grabbed sushi for $32 last night"',
              '"paid $14.99 for Spotify"',
              '"filled up the car, $65"',
            ].map((ex) => (
              <span
                key={ex}
                className="px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-slate-300 font-mono"
              >
                {ex}
              </span>
            ))}
          </div>
          <p className="text-slate-500 text-sm mt-4">
            → Claude parses amount, category, date, and description automatically
          </p>
        </div>
      </section>

      {/* Features */}
      <section className="max-w-5xl mx-auto px-6 pb-20">
        <h2 className="text-2xl font-bold text-slate-900 text-center mb-10">Everything you need</h2>
        <div className="grid grid-cols-3 gap-5">
          {features.map(({ icon, title, desc }) => (
            <div key={title} className="p-5 bg-slate-50 rounded-xl border border-slate-100">
              <span className="text-2xl block mb-3">{icon}</span>
              <h3 className="text-sm font-semibold text-slate-900 mb-1">{title}</h3>
              <p className="text-xs text-slate-500 leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="border-t border-slate-100 py-16 text-center">
        <h2 className="text-2xl font-bold text-slate-900 mb-3">Ready to start tracking?</h2>
        <p className="text-slate-500 text-sm mb-6">Free to use. No credit card required.</p>
        <Link
          to="/register"
          className="inline-block px-8 py-3 bg-indigo-600 text-white text-sm font-semibold rounded-xl hover:bg-indigo-700 transition-colors shadow-sm"
        >
          Create your account →
        </Link>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-100 py-6 text-center">
        <p className="text-xs text-slate-400">
          Built with FastAPI · React · Supabase · Claude API
        </p>
      </footer>
    </div>
  )
}
