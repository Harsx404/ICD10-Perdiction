import { useEffect, useState } from "react";
import { AlertTriangle, Download, FileText } from "lucide-react";

interface Props {
  docId: string;
}

export default function PdfViewer({ docId }: Props) {
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let url: string | null = null;
    setError(false);
    setBlobUrl(null);

    fetch(`/api/v1/analyses/${docId}/pdf`)
      .then((response) => {
        if (!response.ok) throw new Error(`${response.status}`);
        return response.blob();
      })
      .then((blob) => {
        url = URL.createObjectURL(blob);
        setBlobUrl(url);
      })
      .catch(() => setError(true));

    return () => {
      if (url) URL.revokeObjectURL(url);
    };
  }, [docId]);

  if (error) {
    return (
      <div className="flex min-h-[220px] flex-col items-center justify-center gap-4 rounded-[1.75rem] border border-red-100 bg-red-50 p-8 text-center">
        <AlertTriangle className="h-8 w-8 text-red-500" />
        <div>
          <p className="text-base font-semibold text-red-700">Could not load PDF preview</p>
          <p className="mt-2 text-sm text-red-600">
            The report may still be available as a direct file download.
          </p>
        </div>
        <a
          href={`/api/v1/analyses/${docId}/pdf`}
          download
          className="inline-flex items-center gap-2 rounded-full bg-white px-4 py-2 text-sm font-semibold text-red-600 shadow-sm"
        >
          <Download className="h-4 w-4" />
          Download PDF
        </a>
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-[1.75rem] border border-slate-200 bg-white shadow-card">
      <div className="flex flex-col gap-3 border-b border-slate-200 bg-slate-50/80 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-brand-50 text-brand-600">
            <FileText className="h-5 w-5" />
          </span>
          <div>
            <p className="text-sm font-semibold text-slate-900">Saved PDF report</p>
            <p className="text-xs text-slate-500">Document ID: {docId}</p>
          </div>
        </div>
        <a
          href={`/api/v1/analyses/${docId}/pdf`}
          download={`report-${docId}.pdf`}
          className="inline-flex items-center gap-2 rounded-full bg-white px-4 py-2 text-sm font-semibold text-brand-600 shadow-sm transition-colors hover:bg-brand-50"
        >
          <Download className="h-4 w-4" />
          Download PDF
        </a>
      </div>

      {blobUrl ? (
        <iframe
          src={blobUrl}
          className="min-h-[720px] w-full"
          title="Clinical Analysis PDF Report"
        />
      ) : (
        <div className="flex min-h-[260px] items-center justify-center text-sm font-medium text-slate-400">
          Loading saved PDF report...
        </div>
      )}
    </div>
  );
}
