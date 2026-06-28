"use client";

import { useState } from "react";

interface RepoInputProps {
  onIndexed: (repoId: number) => void;
}

export default function RepoInput({ onIndexed }: RepoInputProps) {
  const [url, setUrl] = useState("");
  const [status, setStatus] = useState<"idle" | "indexing" | "ready" | "failed">("idle");
  const [message, setMessage] = useState("");

  async function handleIndex() {
    if (!url.trim()) return;
    setStatus("indexing");
    setMessage("Starting indexing...");

    // Call POST /index
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/index`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ github_url: url }),
    });
    const data = await res.json();
    const repoId = data.repo_id;

    // Poll GET /status every 2 seconds until ready or failed
    const interval = setInterval(async () => {
      const statusRes = await fetch(`http://localhost:8000/status/${repoId}`);
      const statusData = await statusRes.json();

      if (statusData.status === "ready") {
        clearInterval(interval);
        setStatus("ready");
        setMessage(`Indexed ${statusData.indexed_chunk_count} chunks successfully`);
        onIndexed(repoId);
      } else if (statusData.status === "failed") {
        clearInterval(interval);
        setStatus("failed");
        setMessage("Indexing failed. Check the repo URL and try again.");
      } else {
        setMessage("Indexing in progress...");
      }
    }, 2000);
  }

  return (
    <div className="w-full max-w-2xl mx-auto">
      <h1 className="text-3xl font-bold text-center mb-2 text-white">
        reposage
      </h1>
      <p className="text-center text-gray-400 mb-8 text-sm">
        Ask questions about any public GitHub repo
      </p>

      <div className="flex gap-2">
        <input
          type="text"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://github.com/owner/repo"
          className="flex-1 bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
          disabled={status === "indexing"}
          onKeyDown={(e) => e.key === "Enter" && handleIndex()}
        />
        <button
          onClick={handleIndex}
          disabled={status === "indexing" || !url.trim()}
          className="bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:cursor-not-allowed text-white px-6 py-3 rounded-lg font-medium transition-colors"
        >
          {status === "indexing" ? "Indexing..." : "Index"}
        </button>
      </div>

      {message && (
        <p className={`mt-3 text-sm text-center ${
          status === "failed" ? "text-red-400" :
          status === "ready" ? "text-green-400" :
          "text-yellow-400"
        }`}>
          {status === "indexing" && (
            <span className="inline-block w-3 h-3 border-2 border-yellow-400 border-t-transparent rounded-full animate-spin mr-2 align-middle" />
          )}
          {message}
        </p>
      )}
    </div>
  );
}