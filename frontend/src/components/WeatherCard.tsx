import {
  CloudSun,
  Droplets,
  Thermometer,
  Wind,
} from "lucide-react";

import { extractMcpTexts } from "../utils/mcpParser";

interface WeatherCardProps {
  content: string;
}

interface WeatherData {
  city?: string;
  temperature_c?: number;
  feels_like_c?: number;
  humidity?: number;
  condition?: string;
  wind_speed?: number;
}

interface ForecastData {
  city?: string;
  forecast?: {
    datetime: string;
    temperature_c: number;
    condition: string;
  }[];
}

export default function WeatherCard({
  content,
}: WeatherCardProps) {
  const texts = extractMcpTexts(content);

  let current: WeatherData | null = null;
  let forecast: ForecastData | null = null;

  for (const text of texts) {
    try {
      const parsed = JSON.parse(text);

      if (parsed.forecast) {
        forecast = parsed;
      } else if (
        parsed.temperature_c !== undefined
      ) {
        current = parsed;
      }
    } catch {
      continue;
    }
  }

  {/* Fallback */}
  if (!current) {
    return (
      <section className="rounded-2xl border border-white/10 bg-white/[0.03] p-5">
        <div className="mb-5 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-400/10">
            <CloudSun
              size={20}
              className="text-amber-400"
            />
          </div>

          <div>
            <h3 className="font-semibold text-white">
              Weather
            </h3>

            <p className="text-xs text-slate-500">
              Destination conditions
            </p>
          </div>
        </div>

        <div className="rounded-xl border border-amber-400/10 bg-amber-400/[0.03] p-4">
          <p className="text-xs leading-5 text-slate-500">
            Weather data could not be structured from the
            provider response.
          </p>
        </div>
      </section>
    );
  }

  return (
    <section className="rounded-2xl border border-white/10 bg-white/[0.03] p-5">
      {/* Header */}
      <div className="mb-5 flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-400/10">
          <CloudSun
            size={20}
            className="text-amber-400"
          />
        </div>

        <div>
          <h3 className="font-semibold text-white">
            {current.city || "Destination"} Weather
          </h3>

          <p className="text-xs text-slate-500">
            Current conditions
          </p>
        </div>
      </div>

      {/* Current weather */}
      <div className="rounded-xl border border-white/5 bg-black/20 p-5">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-4xl font-bold text-white">
              {current.temperature_c}°
              <span className="text-lg text-slate-500">
                C
              </span>
            </p>

            <p className="mt-1 capitalize text-sm text-slate-400">
              {current.condition}
            </p>
          </div>

          <CloudSun
            size={48}
            className="text-amber-400/70"
          />
        </div>

        {/* Metrics */}
        <div className="mt-5 grid grid-cols-3 gap-2">
          <div className="rounded-lg bg-white/[0.03] p-3">
            <Thermometer
              size={14}
              className="text-slate-500"
            />

            <p className="mt-2 text-[10px] text-slate-600">
              Feels like
            </p>

            <p className="text-xs font-medium text-slate-300">
              {current.feels_like_c}°C
            </p>
          </div>

          <div className="rounded-lg bg-white/[0.03] p-3">
            <Droplets
              size={14}
              className="text-blue-400"
            />

            <p className="mt-2 text-[10px] text-slate-600">
              Humidity
            </p>

            <p className="text-xs font-medium text-slate-300">
              {current.humidity}%
            </p>
          </div>

          <div className="rounded-lg bg-white/[0.03] p-3">
            <Wind
              size={14}
              className="text-cyan-400"
            />

            <p className="mt-2 text-[10px] text-slate-600">
              Wind
            </p>

            <p className="text-xs font-medium text-slate-300">
              {current.wind_speed} m/s
            </p>
          </div>
        </div>
      </div>

      {/* Forecast */}
      {forecast?.forecast &&
        forecast.forecast.length > 0 && (
          <div className="mt-5">
            <p className="mb-3 text-xs font-medium text-slate-400">
              Forecast
            </p>

            <div className="flex gap-2 overflow-x-auto pb-1">
              {forecast.forecast
                .slice(0, 5)
                .map((day, index) => (
                  <div
                    key={`${day.datetime}-${index}`}
                    className="min-w-[100px] rounded-xl border border-white/5 bg-black/20 p-3"
                  >
                    <p className="text-[10px] text-slate-600">
                      {new Date(
                        day.datetime,
                      ).toLocaleDateString("en-IN", {
                        day: "numeric",
                        month: "short",
                      })}
                    </p>

                    <p className="mt-2 text-lg font-semibold text-white">
                      {Math.round(day.temperature_c)}°
                    </p>

                    <p className="mt-1 truncate text-[10px] capitalize text-slate-500">
                      {day.condition}
                    </p>
                  </div>
                ))}
            </div>
          </div>
        )}
    </section>
  );
}