import { ArrowUp, Sparkles } from "lucide-react";
import { useState } from "react";

interface TripInputProps {
  onSubmit: (message: string) => void;
  loading?: boolean;
}

export default function TripInput({
  onSubmit,
  loading = false,
}: TripInputProps) {
  const [message, setMessage] = useState("");

  const handleSubmit = () => {
    const trimmed = message.trim();

    if (!trimmed || loading) {
      return;
    }

    onSubmit(trimmed);
    setMessage("");
  };

  const handleKeyDown = (
    event: React.KeyboardEvent<HTMLTextAreaElement>,
  ) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="w-full max-w-3xl">
      <div className="mb-3 flex items-center gap-2 text-xs text-slate-500">
        <Sparkles size={14} className="text-cyan-400" />
        Describe your trip naturally
      </div>

      <div className="relative overflow-hidden rounded-2xl border border-white/10 bg-white/[0.04] shadow-2xl shadow-black/20 transition focus-within:border-cyan-400/40 focus-within:ring-1 focus-within:ring-cyan-400/20">
        <textarea
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          onKeyDown={handleKeyDown}
          disabled={loading}
          rows={4}
          placeholder="Plan a 3-day trip to Delhi for 2 people with a budget of ₹30,000..."
          className="w-full resize-none bg-transparent px-5 py-5 pr-16 text-sm leading-6 text-white outline-none placeholder:text-slate-600 disabled:opacity-50"
        />

        <button
          onClick={handleSubmit}
          disabled={!message.trim() || loading}
          className="absolute bottom-4 right-4 flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-400 to-blue-600 text-white shadow-lg shadow-cyan-500/20 transition hover:scale-105 disabled:cursor-not-allowed disabled:opacity-30"
        >
          <ArrowUp size={19} />
        </button>
      </div>

      <p className="mt-3 text-center text-[11px] text-slate-600">
        TripMate uses multiple AI agents to build your travel plan.
      </p>
    </div>
  );
}