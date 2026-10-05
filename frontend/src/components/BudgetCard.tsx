import {
  Wallet,
  Plane,
  Hotel,
  Utensils,
  Car,
  Ticket,
  MoreHorizontal,
} from "lucide-react";

interface BudgetCardProps {
  content: string;
}

function getIcon(category: string) {
  const value = category.toLowerCase();

  if (value.includes("flight")) return Plane;
  if (value.includes("hotel")) return Hotel;
  if (value.includes("food") || value.includes("meal")) return Utensils;
  if (value.includes("transport")) return Car;
  if (value.includes("attraction")) return Ticket;

  return MoreHorizontal;
}

export default function BudgetCard({
  content,
}: BudgetCardProps) {
  let budgetData: {
    category: string;
    amount: string;
    notes?: string;
  }[] = [];

  try {
    const parsed = JSON.parse(content);

    if (Array.isArray(parsed)) {
      budgetData = parsed;
    } else if (parsed.categories) {
      budgetData = parsed.categories;
    }
  } catch {
    // Backend may return markdown/text.
  }

  return (
    <section className="rounded-2xl border border-white/10 bg-white/[0.03] p-5">
      <div className="mb-5 flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-400/10">
          <Wallet size={19} className="text-emerald-400" />
        </div>

        <div>
          <h3 className="font-semibold text-white">
            Trip Budget
          </h3>
          <p className="text-xs text-slate-500">
            Estimated expenses
          </p>
        </div>
      </div>

      {budgetData.length > 0 ? (
        <div className="space-y-2">
          {budgetData.map((item, index) => {
            const Icon = getIcon(item.category);

            return (
              <div
                key={`${item.category}-${index}`}
                className="flex items-center gap-3 rounded-xl bg-black/20 p-3"
              >
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-white/5">
                  <Icon size={15} className="text-emerald-400" />
                </div>

                <div className="min-w-0 flex-1">
                  <p className="text-xs font-medium text-slate-300">
                    {item.category}
                  </p>

                  {item.notes && (
                    <p className="mt-0.5 truncate text-[10px] text-slate-600">
                      {item.notes}
                    </p>
                  )}
                </div>

                <p className="text-sm font-semibold text-white">
                  {item.amount}
                </p>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="rounded-xl bg-black/20 p-4">
          <p className="whitespace-pre-wrap text-sm leading-6 text-slate-400">
            {content}
          </p>
        </div>
      )}
    </section>
  );
}