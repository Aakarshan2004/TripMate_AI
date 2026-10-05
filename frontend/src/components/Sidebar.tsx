import {
  Compass,
  Plus,
  MapPin,
  MessageSquare,
  Settings,
  Sparkles,
} from "lucide-react";

interface SidebarProps {
  onNewTrip: () => void;
}

const recentTrips = [
  "Delhi Adventure",
  "Manali Escape",
  "Goa Getaway",
];

export default function Sidebar({ onNewTrip }: SidebarProps) {
  return (
    <aside className="flex h-screen w-72 shrink-0 flex-col border-r border-white/10 bg-slate-950/80 px-5 py-6 backdrop-blur-xl">
      {/* Logo */}
      <div className="mb-8 flex items-center gap-3 px-2">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-400 to-blue-600 shadow-lg shadow-cyan-500/20">
          <Compass size={22} className="text-white" />
        </div>

        <div>
          <h1 className="text-lg font-bold tracking-tight text-white">
            TripMate
          </h1>
          <p className="text-[11px] text-slate-500">AI Travel Planner</p>
        </div>
      </div>

      {/* New Trip */}
      <button
        onClick={onNewTrip}
        className="mb-8 flex w-full items-center justify-center gap-2 rounded-xl bg-white px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-50 hover:shadow-lg hover:shadow-cyan-500/10"
      >
        <Plus size={18} />
        New Trip
      </button>

      {/* Recent */}
      <div className="flex-1">
        <div className="mb-3 flex items-center gap-2 px-2">
          <MessageSquare size={14} className="text-slate-500" />
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Recent Trips
          </span>
        </div>

        <div className="space-y-1">
          {recentTrips.map((trip) => (
            <button
              key={trip}
              className="group flex w-full items-center gap-3 rounded-lg px-3 py-3 text-left text-sm text-slate-400 transition hover:bg-white/5 hover:text-white"
            >
              <MapPin
                size={15}
                className="text-slate-600 transition group-hover:text-cyan-400"
              />
              <span className="truncate">{trip}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Bottom */}
      <div className="border-t border-white/10 pt-4">
        <div className="mb-3 flex items-center gap-2 rounded-xl bg-cyan-400/5 p-3">
          <Sparkles size={16} className="text-cyan-400" />

          <div>
            <p className="text-xs font-medium text-white">
              Powered by LangGraph
            </p>
            <p className="text-[10px] text-slate-500">
              Multi-agent planning
            </p>
          </div>
        </div>

        <button className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-slate-500 transition hover:bg-white/5 hover:text-white">
          <Settings size={16} />
          Settings
        </button>
      </div>
    </aside>
  );
}