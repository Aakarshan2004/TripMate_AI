import FlightCard from "./FlightCard";
import HotelCard from "./HotelCard";
import WeatherCard from "./WeatherCard";
import BudgetCard from "./BudgetCard";
import ItineraryCard from "./ItineraryCard";
import AgentProgress from "./AgentProgress";
import type { AgentStatus } from "./AgentProgress";

interface ResultsDashboardProps {
  flightResults: string;
  hotelResults: string;
  weatherResults: string;
  budgetResults: string;
  itinerary: string;
  agentStatuses?: Record<string, AgentStatus>;
}

export default function ResultsDashboard({
  flightResults,
  hotelResults,
  weatherResults,
  budgetResults,
  itinerary,
  agentStatuses,
}: ResultsDashboardProps) {
  return (
    <div className="w-full max-w-5xl space-y-5">
      <AgentProgress statuses={agentStatuses} />

      <div className="grid gap-5 lg:grid-cols-2">
        <FlightCard content={flightResults} />
        <HotelCard content={hotelResults} />
        <WeatherCard content={weatherResults} />
        <BudgetCard content={budgetResults} />
      </div>

      <ItineraryCard content={itinerary} />
    </div>
  );
}