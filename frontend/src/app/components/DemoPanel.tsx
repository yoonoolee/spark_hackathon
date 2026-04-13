import { useEffect, useRef, useState } from "react";
import { api } from "@/api/client";
import { useAppContext } from "@/app/context/AppContext";

const USER_ID = 1;
const POLL_MS = 2500;

// Line-by-line diff: returns each line tagged as "same" | "changed" | "added"
function diffLines(original: string, updated: string) {
  const origLines = original.split("\n");
  const updLines = updated.split("\n");
  const origSet = new Set(origLines);

  return updLines.map((line) => ({
    text: line,
    status: origSet.has(line) ? ("same" as const) : ("changed" as const),
  }));
}

function DiffContent({ original, updated }: { original: string; updated: string }) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [updated]);

  const lines = diffLines(original, updated);

  return (
    <div
      ref={scrollRef}
      className="h-full overflow-y-auto p-4 text-xs font-mono leading-relaxed"
    >
      {lines.map((line, i) =>
        line.status === "changed" ? (
          <div key={i} className="text-red-600 font-bold -mx-4 px-4 bg-red-50">
            {line.text || "\u00A0"}
          </div>
        ) : (
          <div key={i} className="text-gray-900">
            {line.text || "\u00A0"}
          </div>
        )
      )}
    </div>
  );
}

function ProfileCard({
  label,
  accentColor,
  empty,
  children,
}: {
  label: string;
  accentColor: string;
  empty?: boolean;
  children?: React.ReactNode;
}) {
  return (
    <div className="flex-1 min-h-0 bg-white border border-gray-200 rounded-2xl flex flex-col overflow-hidden">
      <div className="flex items-center gap-2 px-4 py-2.5 border-b border-gray-200 bg-gray-50 flex-none">
        <span className={`w-2 h-2 rounded-full flex-none ${accentColor}`} />
        <span className="text-xs font-mono font-semibold tracking-wider uppercase text-gray-500">
          {label}
        </span>
      </div>
      <div className="flex-1 min-h-0 overflow-hidden">
        {empty ? (
          <p className="text-gray-400 text-xs font-mono p-4 italic">
            No changes yet — complete check-in or give feedback
          </p>
        ) : (
          children
        )}
      </div>
    </div>
  );
}

export function DemoPanel() {
  const { dayOffset } = useAppContext();
  const [sessionStart, setSessionStart] = useState("");
  const [latest, setLatest] = useState("");
  const [animating, setAnimating] = useState(false);

  // Fetch initial profile
  useEffect(() => {
    api.getUser(USER_ID).then((user) => {
      const profile = user.profile_summary ?? "(no profile yet)";
      setSessionStart(profile);
      setLatest(profile);
    }).catch(console.error);
  }, []);

  // Poll for updates
  useEffect(() => {
    const id = setInterval(() => {
      api.getUser(USER_ID).then((user) => {
        if (user.profile_summary) setLatest(user.profile_summary);
      }).catch(() => {});
    }, POLL_MS);
    return () => clearInterval(id);
  }, []);

  // When dayOffset advances, shift "updated" up to "original"
  useEffect(() => {
    if (dayOffset === 0) return;
    setAnimating(true);
    setTimeout(() => {
      setSessionStart((prev) => latest || prev);
      setAnimating(false);
    }, 400);
  }, [dayOffset]);

  const hasUpdate = !!latest && latest !== sessionStart;
  const dayNumber = dayOffset + 1;

  return (
    <div className="h-full flex flex-col gap-3 py-3 pr-3">
      {/* Original profile */}
      <div
        className="flex-1 min-h-0 flex flex-col transition-all duration-400"
        style={{ opacity: animating ? 0.4 : 1, transform: animating ? "translateY(-8px)" : "none" }}
      >
        <ProfileCard
          label={`Day ${dayNumber} · Original`}
          accentColor="bg-emerald-400"
          empty={!sessionStart}
        >
          <pre className="h-full overflow-y-auto p-4 text-xs font-mono text-gray-900 leading-relaxed whitespace-pre-wrap break-words">
            {sessionStart}
          </pre>
        </ProfileCard>
      </div>

      {/* Updated profile — changed lines highlighted red */}
      <div
        className="flex-1 min-h-0 flex flex-col transition-all duration-400"
        style={{ opacity: animating ? 0.4 : 1, transform: animating ? "translateY(-8px)" : "none" }}
      >
        <ProfileCard
          label={`Day ${dayNumber} · After Interactions`}
          accentColor="bg-blue-400"
          empty={!hasUpdate}
        >
          <DiffContent original={sessionStart} updated={latest} />
        </ProfileCard>
      </div>
    </div>
  );
}
