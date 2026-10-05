import {
  Hotel,
  MapPin,
  Star,
  Wifi,
  ExternalLink,
} from "lucide-react";

import { extractMcpJson } from "../utils/mcpParser";

interface HotelCardProps {
  content: string;
}

interface HotelData {
  name: string;
  area: string;
  rating: string;
  reviews: string;
  price: string;
  amenities: string[];
  url: string;
}

interface HotelResponse {
  hotels?: HotelData[];
}

function parseHotels(content: string): HotelData[] {
  const data = extractMcpJson<HotelResponse>(content);

  if (!data?.hotels || !Array.isArray(data.hotels)) {
    return [];
  }

  return data.hotels.filter(
    (hotel) => hotel && typeof hotel.name === "string"
  );
}

export default function HotelCard({ content }: HotelCardProps) {
  const hotels = parseHotels(content);

  if (hotels.length === 0) {
    return (
      <div className="rounded-2xl border border-white/10 bg-slate-900/70 p-6">
        <div className="flex items-center gap-3">
          <Hotel className="h-6 w-6 text-cyan-400" />

          <div>
            <h3 className="text-lg font-semibold text-white">
              Hotel Results
            </h3>

            <p className="mt-1 text-sm text-slate-400">
              No structured hotel results were returned.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {hotels.map((hotel, index) => (
        <div
          key={`${hotel.name}-${index}`}
          className="rounded-2xl border border-white/10 bg-slate-900/70 p-5 shadow-lg"
        >
          {/* Header */}
          <div className="flex items-start justify-between gap-4">
            <div className="flex gap-3">
              <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-cyan-500/10">
                <Hotel className="h-6 w-6 text-cyan-400" />
              </div>

              <div>
                <h3 className="text-lg font-semibold text-white">
                  {hotel.name}
                </h3>

                {hotel.area && (
                  <div className="mt-1 flex items-center gap-1.5 text-sm text-slate-400">
                    <MapPin className="h-4 w-4" />
                    <span>{hotel.area}</span>
                  </div>
                )}
              </div>
            </div>

            {hotel.url && (
              <a
                href={hotel.url}
                target="_blank"
                rel="noopener noreferrer"
                className="rounded-lg p-2 text-slate-400 transition hover:bg-white/5 hover:text-cyan-400"
                title="View source"
              >
                <ExternalLink className="h-5 w-5" />
              </a>
            )}
          </div>

          {/* Rating + Price */}
          <div className="mt-5 grid grid-cols-2 gap-3">
            {hotel.rating && (
              <div className="rounded-xl bg-white/5 p-3">
                <div className="flex items-center gap-2 text-sm text-slate-400">
                  <Star className="h-4 w-4 text-yellow-400" />
                  Rating
                </div>

                <p className="mt-1 font-semibold text-white">
                  {hotel.rating}
                  {hotel.reviews && (
                    <span className="ml-1 text-xs font-normal text-slate-500">
                      ({hotel.reviews} reviews)
                    </span>
                  )}
                </p>
              </div>
            )}

            {hotel.price && (
              <div className="rounded-xl bg-white/5 p-3">
                <p className="text-sm text-slate-400">
                  Approx. price
                </p>

                <p className="mt-1 font-semibold text-white">
                  {hotel.price}
                </p>
              </div>
            )}
          </div>

          {/* Amenities */}
          {hotel.amenities?.length > 0 && (
            <div className="mt-4">
              <div className="mb-2 flex items-center gap-2 text-sm font-medium text-slate-300">
                <Wifi className="h-4 w-4 text-cyan-400" />
                Amenities
              </div>

              <div className="flex flex-wrap gap-2">
                {hotel.amenities.map((amenity, i) => (
                  <span
                    key={i}
                    className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-slate-300"
                  >
                    {amenity}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}