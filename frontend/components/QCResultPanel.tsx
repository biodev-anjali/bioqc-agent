"use client";

import { QCResult } from "@/lib/api";

const STATUS_STYLES: Record<string, string> = {
  pass: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
  warn: "border-amber-500/30 bg-amber-500/10 text-amber-300",
  fail: "border-red-500/30 bg-red-500/10 text-red-300",
  unknown: "border-slate-600 bg-slate-800 text-slate-300",
};

function StatusBadge({ status }: { status: string }) {
  const style = STATUS_STYLES[status.toLowerCase()] ?? STATUS_STYLES.unknown;

  return (
    <span
      className={`inline-flex rounded-lg border px-2.5 py-1 text-xs font-semibold capitalize ${style}`}
    >
      {status}
    </span>
  );
}

interface QCResultPanelProps {
  result: QCResult;
}

export function QCResultPanel({ result }: QCResultPanelProps) {
  const modules = [
    { label: "Per base sequence quality", status: result.per_base_quality_status },
    { label: "Per sequence quality scores", status: result.per_sequence_quality_status },
    { label: "Adapter content", status: result.adapter_content_status },
    { label: "Overrepresented sequences", status: result.overrepresented_sequences_status },
  ];

  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6 shadow-xl shadow-black/20">
      <h2 className="mb-1 text-xl font-semibold">QC results</h2>
      <p className="mb-6 text-sm text-slate-400">
        Parsed from FastQC report on{" "}
        {new Date(result.created_at).toLocaleString()}
      </p>

      <dl className="mb-8 grid gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
          <dt className="text-xs text-slate-400">Total sequences</dt>
          <dd className="mt-2 text-2xl font-semibold">
            {result.total_sequences.toLocaleString()}
          </dd>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
          <dt className="text-xs text-slate-400">Sequence length</dt>
          <dd className="mt-2 text-2xl font-semibold">{result.sequence_length}</dd>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
          <dt className="text-xs text-slate-400">% GC</dt>
          <dd className="mt-2 text-2xl font-semibold">{result.gc_percent}%</dd>
        </div>
      </dl>

      <div>
        <h3 className="mb-3 text-sm font-medium text-slate-200">Module statuses</h3>
        <ul className="space-y-3">
          {modules.map((module) => (
            <li
              key={module.label}
              className="flex items-center justify-between gap-4 rounded-xl border border-slate-800 bg-slate-950/40 px-4 py-3"
            >
              <span className="text-sm text-slate-300">{module.label}</span>
              <StatusBadge status={module.status} />
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
