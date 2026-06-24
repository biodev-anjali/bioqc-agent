"use client";

import { FormEvent, useState } from "react";

import { AnalysisJob, getJobStatus, uploadJobFile } from "@/lib/api";

function formatBytes(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function Home() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [job, setJob] = useState<AnalysisJob | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedFile) {
      setError("Select a file before uploading.");
      return;
    }

    setIsUploading(true);
    setError(null);

    try {
      const response = await uploadJobFile(selectedFile);
      setJob(response.job);
    } catch (uploadError) {
      setError(
        uploadError instanceof Error ? uploadError.message : "Upload failed.",
      );
    } finally {
      setIsUploading(false);
    }
  }

  async function handleRefreshStatus() {
    if (!job) {
      return;
    }

    setIsRefreshing(true);
    setError(null);

    try {
      const latestJob = await getJobStatus(job.id);
      setJob(latestJob);
    } catch (refreshError) {
      setError(
        refreshError instanceof Error
          ? refreshError.message
          : "Unable to refresh job status.",
      );
    } finally {
      setIsRefreshing(false);
    }
  }

  return (
    <div className="min-h-full bg-slate-950 text-slate-100">
      <main className="mx-auto flex w-full max-w-3xl flex-col gap-8 px-6 py-16">
        <header className="space-y-3">
          <p className="text-sm font-medium uppercase tracking-[0.2em] text-emerald-400">
            BioQC Agent
          </p>
          <h1 className="text-4xl font-semibold tracking-tight">
            Upload QC Files
          </h1>
          <p className="max-w-2xl text-base leading-7 text-slate-300">
            Upload FastQC or MultiQC files to create an analysis job. Parsing
            and report generation will be added in later phases.
          </p>
        </header>

        <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6 shadow-xl shadow-black/20">
          <form className="space-y-5" onSubmit={handleUpload}>
            <div className="space-y-2">
              <label
                htmlFor="qc-file"
                className="block text-sm font-medium text-slate-200"
              >
                QC file
              </label>
              <input
                id="qc-file"
                type="file"
                accept=".zip,.html,.gz,.tar.gz"
                className="block w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-100 file:mr-4 file:rounded-lg file:border-0 file:bg-emerald-500 file:px-4 file:py-2 file:text-sm file:font-medium file:text-slate-950 hover:file:bg-emerald-400"
                onChange={(event) => {
                  const file = event.target.files?.[0] ?? null;
                  setSelectedFile(file);
                  setError(null);
                }}
              />
              <p className="text-sm text-slate-400">
                Allowed types: .zip, .html, .gz, .tar.gz (max 100 MB)
              </p>
            </div>

            <button
              type="submit"
              disabled={!selectedFile || isUploading}
              className="inline-flex items-center justify-center rounded-xl bg-emerald-500 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
            >
              {isUploading ? "Uploading..." : "Upload file"}
            </button>
          </form>

          {error ? (
            <p className="mt-4 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
              {error}
            </p>
          ) : null}
        </section>

        {job ? (
          <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
            <div className="mb-4 flex items-center justify-between gap-4">
              <h2 className="text-xl font-semibold">Job status</h2>
              <button
                type="button"
                onClick={handleRefreshStatus}
                disabled={isRefreshing}
                className="rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200 transition hover:border-slate-500 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isRefreshing ? "Refreshing..." : "Refresh"}
              </button>
            </div>

            <dl className="grid gap-4 sm:grid-cols-2">
              <div>
                <dt className="text-sm text-slate-400">Job ID</dt>
                <dd className="mt-1 break-all font-mono text-sm">{job.id}</dd>
              </div>
              <div>
                <dt className="text-sm text-slate-400">Status</dt>
                <dd className="mt-1 text-sm font-medium capitalize">
                  {job.status}
                </dd>
              </div>
              <div>
                <dt className="text-sm text-slate-400">Filename</dt>
                <dd className="mt-1 text-sm">{job.original_filename}</dd>
              </div>
              <div>
                <dt className="text-sm text-slate-400">File type</dt>
                <dd className="mt-1 text-sm">{job.file_type}</dd>
              </div>
              <div>
                <dt className="text-sm text-slate-400">Size</dt>
                <dd className="mt-1 text-sm">{formatBytes(job.file_size)}</dd>
              </div>
              <div>
                <dt className="text-sm text-slate-400">Stored path</dt>
                <dd className="mt-1 break-all text-sm">{job.file_path}</dd>
              </div>
            </dl>
          </section>
        ) : null}
      </main>
    </div>
  );
}
