import type { ClaimVerification } from "../../api/types";
import { CheckCircle2, AlertTriangle, XCircle, Info } from "lucide-react";

interface Props {
  verification: ClaimVerification;
}

function StatusBanner({ status }: { status: ClaimVerification["status"] }) {
  const config = {
    approved: {
      icon: CheckCircle2,
      bg: "bg-emerald-50 border-emerald-100",
      text: "text-emerald-700",
      label: "Claim Approved",
    },
    flagged: {
      icon: AlertTriangle,
      bg: "bg-amber-50 border-amber-100",
      text: "text-amber-700",
      label: "Claim Flagged for Review",
    },
    denied: {
      icon: XCircle,
      bg: "bg-red-50 border-red-100",
      text: "text-red-700",
      label: "Claim Denied",
    },
  }[status];

  const Icon = config.icon;
  return (
    <div className={`flex items-center gap-3 p-5 rounded-2xl border ${config.bg}`}>
      <Icon className={`w-6 h-6 ${config.text}`} />
      <span className={`text-base font-bold ${config.text}`}>{config.label}</span>
    </div>
  );
}

export default function ClaimVerifier({ verification }: Props) {
  return (
    <div className="space-y-6">
      <StatusBanner status={verification.status} />

      {verification.issues.length > 0 && (
        <div>
          <h4 className="text-sm font-bold text-gray-800 uppercase tracking-widest mb-3">Issues</h4>
          <div className="space-y-3">
            {verification.issues.map((issue, i) => {
              const Icon =
                issue.severity === "error"
                  ? XCircle
                  : issue.severity === "warning"
                    ? AlertTriangle
                    : Info;
              const cls =
                issue.severity === "error"
                  ? "text-red-600 bg-red-50 border-red-100"
                  : issue.severity === "warning"
                    ? "text-amber-600 bg-amber-50 border-amber-100"
                    : "text-brand-600 bg-brand-50 border-brand-100";
              const iconCls =
                issue.severity === "error"
                  ? "text-red-600"
                  : issue.severity === "warning"
                    ? "text-amber-600"
                    : "text-brand-600";
              return (
                <div
                  key={i}
                  className={`flex flex-col gap-2 p-4 rounded-2xl border ${cls}`}
                >
                  <div className="flex items-center gap-2">
                    <Icon className={`w-4 h-4 ${iconCls} flex-shrink-0`} />
                    <code className="text-[11px] font-bold uppercase tracking-widest">{issue.code}</code>
                  </div>
                  <p className="text-[13px] font-semibold">{issue.message}</p>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {verification.recommendations.length > 0 && (
        <div className="pt-2">
          <h4 className="text-[11px] font-bold text-gray-400 uppercase tracking-widest mb-3 px-1">Recommendations</h4>
          <ul className="space-y-2">
            {verification.recommendations.map((r, i) => (
              <li key={i} className="text-sm font-medium text-gray-600 bg-gray-50 p-3 rounded-xl border border-gray-100">
                {r}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
