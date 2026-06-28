"use client";

import { useState } from "react";

interface Source {
  file_path: string;
  start_line: number;
  end_line: number;
}

interface Message {
  question: string;
  answer: string;
  sources: Source[];
}

interface ChatBoxProps {
  repoId: number;
}

export default function ChatBox({ repoId }: ChatBoxProps) {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [currentAnswer, setCurrentAnswer] = useState("");
  const [currentSources, setCurrentSources] = useState<Source[]>([]);

  async function handleAsk() {
    if (!question.trim() || loading) return;

    const q = question.trim();
    setQuestion("");
    setLoading(true);
    setCurrentAnswer("");
    setCurrentSources([]);

    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ repo_id: repoId, question: q }),
    });

    const reader = response.body!.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let sources: Source[] = [];
    let answer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const raw = line.slice(6).trim();
          if (!raw || raw === "{}") continue;

          try {
            const parsed = JSON.parse(raw);
            if (Array.isArray(parsed)) {
              // sources event
              sources = parsed;
              setCurrentSources(parsed);
            } else if (parsed.text) {
              // token event
              answer += parsed.text;
              setCurrentAnswer((prev) => prev + parsed.text);
            }
          } catch {
            // ignore malformed lines
          }
        }
      }
    }

    // Save completed message to history
    setMessages((prev) => [...prev, { question: q, answer, sources }]);
    setCurrentAnswer("");
    setCurrentSources([]);
    setLoading(false);
  }

  // Clean up temp path from file_path so it shows relative path only
  function cleanPath(filePath: string): string {
    const parts = filePath.split("/");
    // Find the repo folder (after the temp dir) and show from there
    const repoIndex = parts.findIndex((p) => p.startsWith("reposage_") || p === "T");
    if (repoIndex !== -1 && parts[repoIndex + 1]?.startsWith("reposage_")) {
      return parts.slice(repoIndex + 2).join("/");
    }
    // Fallback: just show last 3 path segments
    return parts.slice(-3).join("/");
  }

  return (
    <div className="w-full max-w-3xl mx-auto mt-10">
      {/* Message history */}
      <div className="space-y-8 mb-8">
        {messages.map((msg, i) => (
          <div key={i} className="space-y-3">
            {/* Question */}
            <div className="flex justify-end">
              <div className="bg-blue-600 text-white px-4 py-2 rounded-2xl rounded-tr-sm max-w-lg text-sm">
                {msg.question}
              </div>
            </div>

            {/* Sources */}
            {msg.sources.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {msg.sources.map((s, j) => (
                  <span
                    key={j}
                    className="text-xs bg-gray-800 text-gray-300 px-2 py-1 rounded-md font-mono"
                  >
                    {cleanPath(s.file_path)}:{s.start_line}-{s.end_line}
                  </span>
                ))}
              </div>
            )}

            {/* Answer */}
            <div className="bg-gray-900 border border-gray-800 rounded-2xl rounded-tl-sm px-4 py-3 text-sm text-gray-100 leading-relaxed whitespace-pre-wrap">
              {msg.answer}
            </div>
          </div>
        ))}

        {/* Streaming answer (in progress) */}
        {loading && (
          <div className="space-y-3">
            {currentSources.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {currentSources.map((s, j) => (
                  <span
                    key={j}
                    className="text-xs bg-gray-800 text-gray-300 px-2 py-1 rounded-md font-mono"
                  >
                    {cleanPath(s.file_path)}:{s.start_line}-{s.end_line}
                  </span>
                ))}
              </div>
            )}
            <div className="bg-gray-900 border border-gray-800 rounded-2xl rounded-tl-sm px-4 py-3 text-sm text-gray-100 leading-relaxed whitespace-pre-wrap">
              {currentAnswer || (
                <span className="flex items-center gap-2 text-gray-500">
                  <span className="inline-block w-3 h-3 border-2 border-gray-500 border-t-transparent rounded-full animate-spin" />
                  Thinking...
                </span>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="flex gap-2 sticky bottom-4">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleAsk()}
          placeholder="Ask anything about this repo..."
          disabled={loading}
          className="flex-1 bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 text-sm"
        />
        <button
          onClick={handleAsk}
          disabled={loading || !question.trim()}
          className="bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:cursor-not-allowed text-white px-6 py-3 rounded-lg font-medium transition-colors text-sm"
        >
          Ask
        </button>
      </div>
    </div>
  );
}