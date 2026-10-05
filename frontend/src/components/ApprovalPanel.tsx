import { Check, Edit3, ShieldCheck } from "lucide-react";
import { useState } from "react";

interface ApprovalPanelProps {
  onApprove: () => void;
  onRevise: (feedback: string) => void;
  loading?: boolean;
}

export default function ApprovalPanel({
  onApprove,
  onRevise,
  loading = false,
}: ApprovalPanelProps) {
  const [showRevision, setShowRevision] = useState(false);
  const [feedback, setFeedback] = useState("");

  const handleRevision = () => {
    if (!feedback.trim() || loading) return;

    onRevise(feedback.trim());
    setFeedback("");
  };

  return (
    <section className="rounded-2xl border border-cyan-400/20 bg-cyan-400/[0.04] p-6">
      <div className="flex items-start gap-4">
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-cyan-400/10">
          <ShieldCheck size={21} className="text-cyan-400" />
        </div>

        <div className="flex-1">
          <p className="text-xs font-semibold uppercase tracking-wider text-cyan-400">
            Human Review Required
          </p>

          <h3 className="mt-1 text-lg font-semibold text-white">
            Your trip plan is ready
          </h3>

          <p className="mt-2 text-sm leading-6 text-slate-500">
            Review the recommendations before finalizing your travel plan.
            You can approve it or ask the AI agents to revise it.
          </p>

          {!showRevision ? (
            <div className="mt-5 flex flex-wrap gap-3">
              <button
                onClick={onApprove}
                disabled={loading}
                className="flex items-center gap-2 rounded-xl bg-emerald-500 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-emerald-400 disabled:opacity-50"
              >
                <Check size={17} />
                {loading ? "Processing..." : "Approve Plan"}
              </button>

              <button
                onClick={() => setShowRevision(true)}
                disabled={loading}
                className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-5 py-2.5 text-sm font-semibold text-slate-300 transition hover:bg-white/10 hover:text-white disabled:opacity-50"
              >
                <Edit3 size={16} />
                Request Changes
              </button>
            </div>
          ) : (
            <div className="mt-5">
              <textarea
                value={feedback}
                onChange={(event) => setFeedback(event.target.value)}
                rows={3}
                placeholder="What would you like to change? e.g. Find cheaper hotels..."
                className="w-full resize-none rounded-xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-white outline-none placeholder:text-slate-600 focus:border-cyan-400/40"
              />

              <div className="mt-3 flex gap-3">
                <button
                  onClick={handleRevision}
                  disabled={!feedback.trim() || loading}
                  className="rounded-xl bg-cyan-500 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-cyan-400 disabled:opacity-40"
                >
                  {loading ? "Updating..." : "Submit Revision"}
                </button>

                <button
                  onClick={() => setShowRevision(false)}
                  disabled={loading}
                  className="rounded-xl border border-white/10 px-5 py-2.5 text-sm text-slate-400 transition hover:bg-white/5 hover:text-white"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}