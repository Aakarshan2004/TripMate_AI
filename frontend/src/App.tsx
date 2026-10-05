import { useState } from "react";
import Sidebar from "./components/Sidebar";
import Header from "./components/Header";
import TripInput from "./components/TripInput";
import ResultsDashboard from "./components/ResultsDashboard";
import ApprovalPanel from "./components/ApprovalPanel";
import type { AgentStatus } from "./components/AgentProgress";

const API_BASE_URL = "http://127.0.0.1:8000";

interface TravelResponse {
  success: boolean;
  thread_id?: string;
  requires_approval?: boolean;
  approval_request?: string;
  final_response?: string;

  flight_results?: string;
  hotel_results?: string;
  weather_results?: string;
  budget_results?: string;
  itinerary?: string;

  selected_agents?: string[];

  error?: string;
}

const initialStatuses: Record<string, AgentStatus> = {
  supervisor: "pending",
  flight_agent: "pending",
  hotel_agent: "pending",
  weather_agent: "pending",
  budget_agent: "pending",
  itinerary_agent: "pending",
};

function App() {
  const [tripStarted, setTripStarted] = useState(false);
  const [loading, setLoading] = useState(false);

  const [threadId, setThreadId] = useState("");
  const [requiresApproval, setRequiresApproval] = useState(false);

  const [error, setError] = useState("");

  const [agentStatuses, setAgentStatuses] =
    useState<Record<string, AgentStatus>>(initialStatuses);

  const [results, setResults] = useState({
    flightResults: "",
    hotelResults: "",
    weatherResults: "",
    budgetResults: "",
    itinerary: "",
  });

  const resetTrip = () => {
    setTripStarted(false);
    setLoading(false);
    setThreadId("");
    setRequiresApproval(false);
    setError("");
    setResults({
      flightResults: "",
      hotelResults: "",
      weatherResults: "",
      budgetResults: "",
      itinerary: "",
    });
    setAgentStatuses(initialStatuses);
  };

  const updateAgentStatuses = () => {
    setAgentStatuses({
      supervisor: "completed",
      flight_agent: "completed",
      hotel_agent: "completed",
      weather_agent: "completed",
      budget_agent: "completed",
      itinerary_agent: "completed",
    });
  };

  const handleTripSubmit = async (message: string) => {
    setTripStarted(true);
    setLoading(true);
    setError("");

    setAgentStatuses({
      supervisor: "running",
      flight_agent: "pending",
      hotel_agent: "pending",
      weather_agent: "pending",
      budget_agent: "pending",
      itinerary_agent: "pending",
    });

    try {
      const response = await fetch(`${API_BASE_URL}/api/travel`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message,
          thread_id: null,
        }),
      });

      const data: TravelResponse = await response.json();

      if (!response.ok || !data.success) {
        throw new Error(data.error || "Unable to generate travel plan.");
      }

      setThreadId(data.thread_id || "");
      setRequiresApproval(Boolean(data.requires_approval));

      setResults({
        flightResults: data.flight_results || "No flight information available.",
        hotelResults: data.hotel_results || "No hotel information available.",
        weatherResults:
          data.weather_results || "No weather information available.",
        budgetResults: data.budget_results || "No budget information available.",
        itinerary: data.itinerary || "No itinerary available.",
      });

      updateAgentStatuses();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Something went wrong while planning your trip.",
      );
    } finally {
      setLoading(false);
    }
  };

  const handleApproval = async (
    approved: boolean,
    feedback = "",
  ) => {
    if (!threadId) return;

    setLoading(true);
    setError("");

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/travel/approve`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            thread_id: threadId,
            approved,
            feedback,
          }),
        },
      );

      const data: TravelResponse = await response.json();

      if (!response.ok || !data.success) {
        throw new Error(data.error || "Unable to update the trip plan.");
      }

      setRequiresApproval(Boolean(data.requires_approval));

      setResults((previous) => ({
        flightResults:
          data.flight_results || previous.flightResults,
        hotelResults:
          data.hotel_results || previous.hotelResults,
        weatherResults:
          data.weather_results || previous.weatherResults,
        budgetResults:
          data.budget_results || previous.budgetResults,
        itinerary: data.itinerary || previous.itinerary,
      }));

      updateAgentStatuses();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Something went wrong while updating the plan.",
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen overflow-hidden bg-[#020617] text-white">
      <Sidebar onNewTrip={resetTrip} />

      <main className="flex min-w-0 flex-1 flex-col">
        <Header />

        <section className="flex-1 overflow-y-auto px-6 py-10">
          {!tripStarted ? (
            <div className="flex min-h-[calc(100vh-10rem)] flex-col items-center justify-center">
              <div className="mb-10 max-w-3xl text-center">
                <div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-2xl border border-cyan-400/20 bg-cyan-400/10">
                  <span className="text-2xl">✈️</span>
                </div>

                <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
                  Where will you go{" "}
                  <span className="bg-gradient-to-r from-cyan-300 to-blue-500 bg-clip-text text-transparent">
                    next?
                  </span>
                </h1>

                <p className="mx-auto mt-4 max-w-xl text-sm leading-6 text-slate-500 sm:text-base">
                  Tell TripMate what you have in mind. Our multi-agent AI
                  will research your trip and build a personalized plan.
                </p>
              </div>

              <TripInput
                onSubmit={handleTripSubmit}
                loading={loading}
              />

              <div className="mt-10 flex flex-wrap justify-center gap-2">
                {[
                  "✈️ Flights",
                  "🏨 Hotels",
                  "🌤 Weather",
                  "💰 Budget",
                  "🗓 Itinerary",
                ].map((feature) => (
                  <span
                    key={feature}
                    className="rounded-full border border-white/10 bg-white/[0.03] px-4 py-2 text-xs text-slate-500"
                  >
                    {feature}
                  </span>
                ))}
              </div>
            </div>
          ) : (
            <div className="mx-auto max-w-5xl space-y-6">
              {loading && (
                <div className="rounded-2xl border border-cyan-400/20 bg-cyan-400/5 px-5 py-4 text-sm text-cyan-300">
                  TripMate AI agents are working on your journey...
                </div>
              )}

              {error && (
                <div className="rounded-2xl border border-red-400/20 bg-red-400/5 px-5 py-4 text-sm text-red-300">
                  {error}
                </div>
              )}

              <ResultsDashboard
                flightResults={results.flightResults}
                hotelResults={results.hotelResults}
                weatherResults={results.weatherResults}
                budgetResults={results.budgetResults}
                itinerary={results.itinerary}
                agentStatuses={agentStatuses}
              />

              {requiresApproval && (
                <ApprovalPanel
                  onApprove={() => handleApproval(true)}
                  onRevise={(feedback) =>
                    handleApproval(false, feedback)
                  }
                  loading={loading}
                />
              )}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

export default App;