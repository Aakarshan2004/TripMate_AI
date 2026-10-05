import {
  CalendarDays,
  MapPin,
  Sunrise,
  Sun,
  Sunset,
  Lightbulb,
} from "lucide-react";

import { extractMcpJson } from "../utils/mcpParser";

interface ItineraryCardProps {
  content: string;
}

interface ItineraryDay {
  day: number;
  title: string;
  morning?: string;
  afternoon?: string;
  evening?: string;
  tips?: string;
}

interface ItineraryData {
  headline?: string;
  overview?: string;
  highlights?: string[];
  itinerary?: ItineraryDay[];
}

function getDayIcon(day: number) {
  if (day === 1) return Sunrise;
  if (day === 2) return Sun;
  return Sunset;
}

function parseItinerary(content: string): ItineraryData | null {
  const data = extractMcpJson<ItineraryData>(content);

  if (data?.itinerary && Array.isArray(data.itinerary)) {
    return data;
  }

  // Sometimes the backend may return the JSON directly.
  try {
    const parsed = JSON.parse(content) as ItineraryData;

    if (parsed.itinerary && Array.isArray(parsed.itinerary)) {
      return parsed;
    }
  } catch {
    // Ignore and use fallback below.
  }

  return null;
}

export default function ItineraryCard({
  content,
}: ItineraryCardProps) {
  const data = parseItinerary(content);

  return (
    <section className="rounded-2xl border border-white/10 bg-white/[0.03] p-5 shadow-xl shadow-black/10">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-pink-400/10">
            <CalendarDays
              size={20}
              className="text-pink-400"
            />
          </div>

          <div>
            <h3 className="font-semibold text-white">
              Your Itinerary
            </h3>

            <p className="text-xs text-slate-500">
              Day-by-day travel plan
            </p>
          </div>
        </div>

        <span className="rounded-full border border-pink-400/10 bg-pink-400/5 px-3 py-1 text-[10px] font-medium text-pink-300">
          Itinerary Agent
        </span>
      </div>

      {/* Trip overview */}
      {data?.headline && (
        <div className="mb-5 rounded-xl border border-pink-400/10 bg-pink-400/[0.04] p-5">
          <h4 className="text-lg font-semibold text-white">
            {data.headline}
          </h4>

          {data.overview && (
            <p className="mt-2 text-sm leading-6 text-slate-400">
              {data.overview}
            </p>
          )}

          {data.highlights && data.highlights.length > 0 && (
            <div className="mt-4 flex flex-wrap gap-2">
              {data.highlights.map((highlight, index) => (
                <span
                  key={index}
                  className="rounded-full border border-white/10 bg-white/[0.03] px-3 py-1.5 text-xs text-slate-400"
                >
                  {highlight}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Days */}
      {data?.itinerary && data.itinerary.length > 0 ? (
        <div className="space-y-5">
          {data.itinerary.map((day, index) => {
            const Icon = getDayIcon(index + 1);

            return (
              <div
                key={day.day ?? index}
                className="relative flex gap-4"
              >
                {/* Timeline */}
                <div className="flex flex-col items-center">
                  <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full border border-pink-400/20 bg-pink-400/10">
                    <Icon
                      size={17}
                      className="text-pink-400"
                    />
                  </div>

                  {index < data.itinerary!.length - 1 && (
                    <div className="mt-2 h-full min-h-10 w-px bg-gradient-to-b from-pink-400/20 to-white/5" />
                  )}
                </div>

                {/* Content */}
                <div className="min-w-0 flex-1 rounded-xl border border-white/5 bg-black/20 p-5">
                  <div className="mb-4">
                    <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-pink-400">
                      Day {day.day ?? index + 1}
                    </p>

                    <h4 className="mt-1 text-base font-semibold text-white">
                      {day.title}
                    </h4>
                  </div>

                  <div className="space-y-4">
                    {day.morning && (
                      <div>
                        <p className="mb-1 text-xs font-medium text-amber-400">
                          Morning
                        </p>

                        <p className="text-sm leading-6 text-slate-400">
                          {day.morning}
                        </p>
                      </div>
                    )}

                    {day.afternoon && (
                      <div>
                        <p className="mb-1 text-xs font-medium text-orange-400">
                          Afternoon
                        </p>

                        <p className="text-sm leading-6 text-slate-400">
                          {day.afternoon}
                        </p>
                      </div>
                    )}

                    {day.evening && (
                      <div>
                        <p className="mb-1 text-xs font-medium text-purple-400">
                          Evening
                        </p>

                        <p className="text-sm leading-6 text-slate-400">
                          {day.evening}
                        </p>
                      </div>
                    )}

                    {day.tips && (
                      <div className="mt-4 flex gap-2 rounded-lg border border-white/5 bg-white/[0.02] p-3">
                        <Lightbulb
                          size={14}
                          className="mt-0.5 shrink-0 text-yellow-400"
                        />

                        <p className="text-xs leading-5 text-slate-500">
                          {day.tips}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        /* Fallback */
        <div className="rounded-xl border border-white/5 bg-black/20 p-5">
          <div className="mb-3 flex items-center gap-2 text-xs text-slate-500">
            <MapPin size={13} />
            Travel schedule
          </div>

          <p className="whitespace-pre-wrap text-sm leading-6 text-slate-300">
            {content}
          </p>
        </div>
      )}
    </section>
  );
}