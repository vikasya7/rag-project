"use client";

import { useState } from "react";
import RepoInput from "@/components/RepoInput";
import ChatBox from "@/components/ChatBox";

export default function Home() {
  const [repoId, setRepoId] = useState<number | null>(null);

  return (
    <main className="min-h-screen px-4 py-12">
      <RepoInput onIndexed={(id) => setRepoId(id)} />
      {repoId && <ChatBox repoId={repoId} />}
    </main>
  );
}
