import { IndianRupee } from "lucide-react";
import type { CostEstimate } from "../../api/types";

const inr = (n: number) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(n);

interface Props {
  estimates: CostEstimate[];
}

export default function CostEstimatePanel({ estimates }: Props) {
  if (estimates.length === 0) return null;

  const INR_RATE = 85;
  const totalLow =
    estimates.reduce((sum, estimate) => sum + estimate.estimated_cost_low, 0) *
    INR_RATE;
  const totalHigh =
    estimates.reduce((sum, estimate) => sum + estimate.estimated_cost_high, 0) *
    INR_RATE;

  return (
    <div>
      <h3 className="mb-4 flex items-center gap-2 text-sm font-bold uppercase tracking-widest text-gray-800">
        <IndianRupee className="h-4 w-4 text-emerald-600" />
        Cost Estimates
      </h3>

      <div className="space-y-3">
        {estimates.map((estimate) => (
          <div
            key={estimate.code}
            className="flex flex-col gap-2 rounded-2xl border border-gray-100 bg-gray-50 p-4"
          >
            <div className="flex items-center justify-between">
              <code className="rounded-lg bg-white px-2 py-1 text-[11px] font-bold text-gray-800 shadow-sm">
                {estimate.code}
              </code>
              <p className="text-sm font-black text-emerald-700">
                {inr(estimate.estimated_cost_low * INR_RATE)} -{" "}
                {inr(estimate.estimated_cost_high * INR_RATE)}
              </p>
            </div>
            <p className="text-xs font-semibold text-gray-600">
              {estimate.description}
            </p>
            <p className="text-[10px] font-bold uppercase tracking-widest text-gray-400">
              {estimate.drg_category}
            </p>
          </div>
        ))}
      </div>

      <div className="mt-5 flex items-center justify-between border-t border-gray-100 px-2 pt-4">
        <span className="text-xs font-bold uppercase tracking-widest text-gray-500">
          Estimated Total
        </span>
        <span className="text-base font-black text-emerald-700">
          {inr(totalLow)} - {inr(totalHigh)}
        </span>
      </div>
    </div>
  );
}
