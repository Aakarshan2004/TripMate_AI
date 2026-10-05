import {
  CheckCircle2,
  Circle,
  Loader2,
  Plane,
  Hotel,
  CloudSun,
  Wallet,
  Map,
  Brain,
  ArrowDown,
} from "lucide-react";

export type AgentStatus =
  | "pending"
  | "running"
  | "completed";

interface AgentProgressProps {
  statuses?: Record<string, AgentStatus>;
}

const agents = [
  {
    id: "supervisor",
    label: "Trip Supervisor",
    description: "Understanding your trip",
    icon: Brain,
  },
  {
    id: "flight_agent",
    label: "Flight Agent",
    description: "Checking flight options",
    icon: Plane,
  },
  {
    id: "hotel_agent",
    label: "Hotel Agent",
    description: "Finding accommodation",
    icon: Hotel,
  },
  {
    id: "weather_agent",
    label: "Weather Agent",
    description: "Checking destination weather",
    icon: CloudSun,
  },
  {
    id: "budget_agent",
    label: "Budget Agent",
    description: "Estimating trip expenses",
    icon: Wallet,
  },
  {
    id: "itinerary_agent",
    label: "Itinerary Agent",
    description: "Building your schedule",
    icon: Map,
  },
];

export default function AgentProgress({
  statuses = {},
}: AgentProgressProps) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-5">
      <div className="mb-6">
        <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-cyan-400">
          <Brain size={14} />
          LangGraph Workflow
        </p>

        <div className="mt-1 flex items-center justify-between">
          <div>
            <h3 className="text-base font-semibold text-white">
              AI travel team
            </h3>

            <p className="mt-1 text-xs text-slate-600">
              Multiple specialized agents working together
            </p>
          </div>

          <span className="rounded-full border border-cyan-400/20 bg-cyan-400/5 px-3 py-1 text-[10px] text-cyan-400">
            Multi-Agent
          </span>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {agents.map((agent, index) => {
          const Icon = agent.icon;
          const status = statuses[agent.id] ?? "pending";

          return (
            <div key={agent.id}>
              <div
                className={`group flex items-center gap-3 rounded-xl border p-3 transition ${
                  status === "running"
                    ? "border-cyan-400/30 bg-cyan-400/5 shadow-lg shadow-cyan-500/5"
                    : status === "completed"
                      ? "border-emerald-400/20 bg-emerald-400/[0.04]"
                      : "border-white/5 bg-white/[0.02]"
                }`}
              >
                <div
                  className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${
                    status === "running"
                      ? "bg-cyan-400/10"
                      : status === "completed"
                        ? "bg-emerald-400/10"
                        : "bg-white/5"
                  }`}
                >
                  <Icon
                    size={17}
                    className={
                      status === "running"
                        ? "text-cyan-400"
                        : status === "completed"
                          ? "text-emerald-400"
                          : "text-slate-600"
                    }
                  />
                </div>

                <div className="min-w-0 flex-1">
                  <p className="truncate text-xs font-medium text-slate-200">
                    {agent.label}
                  </p>

                  <p className="mt-0.5 truncate text-[10px] text-slate-600">
                    {status === "running"
                      ? "Working..."
                      : status === "completed"
                        ? "Completed"
                        : agent.description}
                  </p>
                </div>

                {status === "running" && (
                  <Loader2
                    size={15}
                    className="animate-spin text-cyan-400"
                  />
                )}

                {status === "completed" && (
                  <CheckCircle2
                    size={15}
                    className="text-emerald-400"
                  />
                )}

                {status === "pending" && (
                  <Circle
                    size={13}
                    className="text-slate-700"
                  />
                )}
              </div>

              {index < agents.length - 1 && (
                <div className="hidden justify-center py-1 lg:hidden">
                  <ArrowDown
                    size={12}
                    className="text-slate-700"
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}