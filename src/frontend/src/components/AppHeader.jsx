import { Sun, Moon, Terminal, Cpu } from 'lucide-react'

export function AppHeader({ theme, toggleTheme }) {
  return (
    <div className="h-14 bg-bg border-b border-border flex items-center justify-between px-6 shrink-0 select-none">
      {/* Left: Brand */}
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2">
          <Terminal className="w-5 h-5 text-accent" />
          <span className="text-sm font-bold text-text tracking-tight uppercase">
            Desktop App Template
          </span>
        </div>
      </div>

      {/* Right: Controls */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5 px-2 py-1 border border-border text-text/70 text-[10px] font-bold rounded-sm uppercase tracking-wider">
          <Cpu className="w-3 h-3 text-text/70" />
          Local
        </div>

        <button
          onClick={toggleTheme}
          className="h-7 w-7 flex items-center justify-center rounded-sm border border-border bg-panel hover:bg-border text-text/70 hover:text-text transition-colors"
          title={theme === 'dark' ? 'Modo claro' : 'Modo oscuro'}
        >
          {theme === 'dark' ? <Sun className="w-3.5 h-3.5" /> : <Moon className="w-3.5 h-3.5" />}
        </button>
      </div>
    </div>
  )
}
