import { Bell, CircleUserRound, Sparkles } from "lucide-react";

export default function Header() {
  return (
    <header className="flex h-20 items-center justify-between border-b border-white/10 px-8">
      <div>
        <p className="flex items-center gap-2 text-xs font-medium text-cyan-400">
          <Sparkles size={14} />
          AI-POWERED TRAVEL
        </p>

        <h2 className="mt-1 text-xl font-semibold text-white">
          Plan your next adventure
        </h2>
      </div>

      <div className="flex items-center gap-3">
        <button className="rounded-xl border border-white/10 p-2.5 text-slate-400 transition hover:bg-white/5 hover:text-white">
          <Bell size={18} />
        </button>

        <button className="flex items-center gap-2 rounded-xl border border-white/10 px-3 py-2 text-slate-300 transition hover:bg-white/5">
          <CircleUserRound size={19} />
          <span className="hidden text-sm sm:block">Traveler</span>
        </button>
      </div>
    </header>
  );
}