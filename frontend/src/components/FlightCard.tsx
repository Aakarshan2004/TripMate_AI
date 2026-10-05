import {
  Plane,
  Clock3,
  AlertCircle,
  ArrowRight,
  MapPin,
} from "lucide-react";

import { extractMcpJson } from "../utils/mcpParser";

interface FlightCardProps {
  content: string;
}

interface FlightResult {
  flight?: {
    iata?: string;
    icao?: string;
  };
  airline?: {
    name?: string;
  };
  departure?: {
    airport?: string;
    iata?: string;
    scheduled?: string;
    estimated?: string;
  };
  arrival?: {
    airport?: string;
    iata?: string;
    scheduled?: string;
    estimated?: string;
  };
}

interface FlightResponse {
  results?: FlightResult[];
  error?: string;
  ok?: boolean;
}

function formatTime(value?: string) {
  if (!value) return "--";

  try {
    return new Date(value).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return value;
  }
}

function getFlightData(content: string): FlightResponse | null {
  const data = extractMcpJson<FlightResponse>(content);

  if (!data || !Array.isArray(data.results)) {
    return null;
  }

  return data;
}

function isUnavailable(content: string) {
  const text = content.toLowerCase();

  return (
    text.includes("unavailable") ||
    text.includes("no usable flight") ||
    text.includes("not available") ||
    text.includes("uvx was not found")
  );
}

export default function FlightCard({ content }: FlightCardProps) {
  const data = getFlightData(content);
  const unavailable = isUnavailable(content);

  const flights = data?.results ?? [];

  return (
    <section className="rounded-2xl border border-white/10 bg-white/[0.03] p-5 shadow-xl shadow-black/10">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-400/10">
            <Plane size={20} className="text-blue-400" />
          </div>

          <div>
            <h3 className="font-semibold text-white">Flights</h3>
            <p className="text-xs text-slate-500">
              Available flight information
            </p>
          </div>
        </div>

        <span className="rounded-full border border-blue-400/10 bg-blue-400/5 px-3 py-1 text-[10px] font-medium text-blue-300">
          Flight Agent
        </span>
      </div>

      {/* Unavailable */}
      {unavailable && (
        <div className="rounded-xl border border-amber-400/10 bg-amber-400/[0.04] p-5">
          <div className="flex gap-3">
            <AlertCircle
              size={19}
              className="mt-0.5 shrink-0 text-amber-400"
            />

            <div>
              <p className="text-sm font-medium text-amber-300">
                Live flight data unavailable
              </p>

              <p className="mt-2 text-xs leading-5 text-slate-500">
                The configured flight provider did not return usable live
                schedule data. No flight timings or fares have been invented.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Flight cards */}
      {!unavailable && flights.length > 0 && (
        <div className="space-y-4">
          {flights.slice(0, 5).map((flight, index) => {
            const departure = flight.departure;
            const arrival = flight.arrival;

            return (
              <div
                key={index}
                className="rounded-xl border border-white/5 bg-black/20 p-5 transition hover:border-blue-400/20 hover:bg-white/[0.03]"
              >
                {/* Airline */}
                <div className="mb-5 flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-white">
                      {flight.airline?.name || "Airline information unavailable"}
                    </p>

                    {flight.flight?.iata && (
                      <p className="mt-1 text-xs text-slate-500">
                        Flight {flight.flight.iata}
                      </p>
                    )}
                  </div>

                  <Plane size={17} className="text-blue-400" />
                </div>

                {/* Route */}
                <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-3">
                  <div>
                    <p className="text-xl font-semibold text-white">
                      {departure?.iata || "--"}
                    </p>

                    <p className="mt-1 line-clamp-1 text-[11px] text-slate-500">
                      {departure?.airport || "Departure"}
                    </p>

                    <p className="mt-2 flex items-center gap-1 text-xs text-slate-400">
                      <Clock3 size={12} />
                      {formatTime(
                        departure?.scheduled || departure?.estimated,
                      )}
                    </p>
                  </div>

                  <div className="flex flex-col items-center gap-2">
                    <ArrowRight size={18} className="text-blue-400" />

                    <span className="text-[9px] uppercase tracking-wider text-slate-600">
                      Flight
                    </span>
                  </div>

                  <div className="text-right">
                    <p className="text-xl font-semibold text-white">
                      {arrival?.iata || "--"}
                    </p>

                    <p className="mt-1 line-clamp-1 text-[11px] text-slate-500">
                      {arrival?.airport || "Arrival"}
                    </p>

                    <p className="mt-2 flex items-center justify-end gap-1 text-xs text-slate-400">
                      <Clock3 size={12} />
                      {formatTime(arrival?.scheduled || arrival?.estimated)}
                    </p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* No structured data */}
      {!unavailable && flights.length === 0 && (
        <div className="rounded-xl border border-white/5 bg-black/20 p-5">
          <div className="mb-3 flex items-center gap-2 text-xs text-slate-500">
            <MapPin size={13} />
            Flight information
          </div>

          <p className="whitespace-pre-wrap text-sm leading-6 text-slate-300">
            {content}
          </p>
        </div>
      )}
    </section>
  );
}