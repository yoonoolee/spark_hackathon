import { useState, useEffect, useCallback } from "react";
import { useAppContext } from "@/app/context/AppContext";
import {
  Check,
  ThumbsUp,
  ThumbsDown,
  Sparkles,
  ChevronLeft,
  Wind,
  Footprints,
  Dumbbell,
} from "lucide-react";
import { api, type SuggestionsResponse } from "@/api/client";

const USER_ID = 1;

// ── Workout type → display style mapping ──────────────────────────
type WorkoutStyle = {
  Icon: React.ComponentType<{ className?: string }>;
  iconBg: string;
  iconColor: string;
  badgeBg: string;
  badgeText: string;
  badge: string;
};

function getWorkoutStyle(type: string): WorkoutStyle {
  const t = type.toLowerCase();
  if (t.includes("yoga") || t.includes("pilates") || t.includes("stretch") || t.includes("yin") || t.includes("restor")) {
    return { Icon: Wind, iconBg: "bg-amber-100", iconColor: "text-amber-600", badgeBg: "bg-amber-100", badgeText: "text-amber-700", badge: "Flexibility" };
  }
  if (t.includes("hiit") || t.includes("circuit") || t.includes("interval") || t.includes("boot camp")) {
    return { Icon: Dumbbell, iconBg: "bg-coral-100", iconColor: "text-coral-600", badgeBg: "bg-coral-100", badgeText: "text-coral-700", badge: "High Intensity" };
  }
  if (t.includes("strength") || t.includes("weight") || t.includes("lift") || t.includes("resistance") || t.includes("power")) {
    return { Icon: Dumbbell, iconBg: "bg-lavender-100", iconColor: "text-lavender-600", badgeBg: "bg-lavender-100", badgeText: "text-lavender-700", badge: "Muscle Build" };
  }
  if (t.includes("swim") || t.includes("pool") || t.includes("water") || t.includes("aqua")) {
    return { Icon: Wind, iconBg: "bg-blue-100", iconColor: "text-blue-600", badgeBg: "bg-blue-100", badgeText: "text-blue-700", badge: "Full Body" };
  }
  if (t.includes("run") || t.includes("jog") || t.includes("sprint")) {
    return { Icon: Footprints, iconBg: "bg-emerald-100", iconColor: "text-emerald-600", badgeBg: "bg-emerald-100", badgeText: "text-emerald-700", badge: "Cardio" };
  }
  if (t.includes("cycl") || t.includes("bike") || t.includes("spin")) {
    return { Icon: Footprints, iconBg: "bg-emerald-100", iconColor: "text-emerald-600", badgeBg: "bg-emerald-100", badgeText: "text-emerald-700", badge: "Cardio" };
  }
  if (t.includes("walk") || t.includes("hike")) {
    return { Icon: Footprints, iconBg: "bg-green-100", iconColor: "text-green-600", badgeBg: "bg-green-100", badgeText: "text-green-700", badge: "Low Impact" };
  }
  return { Icon: Wind, iconBg: "bg-lavender-100", iconColor: "text-lavender-600", badgeBg: "bg-lavender-100", badgeText: "text-lavender-700", badge: "Wellness" };
}

function toTitleCase(str: string) {
  return str.replace(/\b\w/g, (c) => c.toUpperCase());
}

// ── Streak Card ───────────────────────────────────────────────────
function StreakCard({ complete, streak }: { complete: boolean; streak: number }) {
  const days = ["M", "T", "W", "T", "F", "S", "S"];
  // Cap visual dots at 7; show actual streak count in text
  const filledDots = complete ? Math.min(streak, 7) : Math.min(Math.max(streak - 1, 0), 6);

  return (
    <div className="mb-5 bg-lavender-50 rounded-3xl p-5 border border-lavender-200">
      <div className="relative flex justify-center items-center mb-3" style={{ height: 64 }}>
        <span className="absolute top-0 left-[30%] text-lavender-300 text-base select-none">✦</span>
        <span className="absolute top-3 right-[28%] text-lavender-200 text-xs select-none">✦</span>
        <span className="absolute bottom-0 left-[20%] text-lavender-400 text-sm select-none">✦</span>
        <span className="absolute top-1 right-[20%] text-lavender-300 text-xs select-none">✦</span>
        <span className="text-5xl leading-none select-none">🔥</span>
      </div>
      <p className="text-center font-semibold text-gray-800 mb-0.5">
        {streak} Day Streak!
      </p>
      <p className="text-center text-xs text-gray-500 mb-4">
        {complete ? "Amazing — you're on fire! 🔥" : "Check in today to keep it going"}
      </p>
      <div className="flex justify-center gap-2">
        {days.map((d, i) => (
          <div key={i} className="flex flex-col items-center gap-1">
            <div
              className={`w-9 h-9 rounded-full flex items-center justify-center transition-all ${
                i < filledDots ? "bg-lavender-500 shadow-sm" : "bg-lavender-100"
              }`}
            >
              {i < filledDots ? (
                <Check className="w-4 h-4 text-white" strokeWidth={3} />
              ) : (
                <span className="text-xs text-lavender-300">{d}</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Inline Check-In Card ──────────────────────────────────────────
type CheckInStep = "feeling" | "energy" | "soreness" | "complete";

const STEPS: CheckInStep[] = ["feeling", "energy", "soreness"];

const stepConfig = {
  feeling: {
    title: "How are you feeling?",
    subtitle: "Step 1 of 3",
    cardBg: "bg-lavender-500",
    lightBg: "bg-lavender-50",
    border: "border-lavender-200",
    options: [
      { emoji: "😊", label: "Great" },
      { emoji: "😌", label: "Good" },
      { emoji: "😐", label: "Okay" },
      { emoji: "😔", label: "Tired" },
      { emoji: "😫", label: "Exhausted" },
      { emoji: "🤕", label: "Unwell" },
    ],
    cols: "grid-cols-3",
  },
  energy: {
    title: "What's your energy level?",
    subtitle: "Step 2 of 3",
    cardBg: "bg-amber-400",
    lightBg: "bg-amber-50",
    border: "border-amber-200",
    options: [
      { emoji: "⚡", label: "High" },
      { emoji: "🔋", label: "Medium" },
      { emoji: "🪫", label: "Low" },
    ],
    cols: "grid-cols-3",
  },
  soreness: {
    title: "Any muscle soreness?",
    subtitle: "Step 3 of 3",
    cardBg: "bg-emerald-500",
    lightBg: "bg-emerald-50",
    border: "border-emerald-200",
    options: [
      { emoji: "💪", label: "None" },
      { emoji: "😅", label: "A Little" },
      { emoji: "🥵", label: "Moderate" },
      { emoji: "😰", label: "Very Sore" },
    ],
    cols: "grid-cols-2",
  },
};

interface CheckInCardProps {
  step: CheckInStep;
  feeling: string;
  energy: string;
  soreness: string;
  onSelect: (val: string) => void;
  onBack: () => void;
  onSubmit: () => void;
  stepIndex: number;
}

function CheckInCard({
  step,
  feeling,
  energy,
  soreness,
  onSelect,
  onBack,
  onSubmit,
  stepIndex,
}: CheckInCardProps) {
  if (step === "complete") return null;
  const cfg = stepConfig[step];
  const currentValue = step === "feeling" ? feeling : step === "energy" ? energy : soreness;
  const progress = ((stepIndex + 1) / 3) * 100;

  return (
    <div className={`mb-5 rounded-3xl overflow-hidden border ${cfg.border} shadow-sm`}>
      <div className={`${cfg.cardBg} px-5 py-4`}>
        <div className="flex items-center justify-between mb-2">
          {stepIndex > 0 ? (
            <button
              onClick={onBack}
              className="flex items-center gap-1 text-white/80 hover:text-white transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
              <span className="text-xs">Back</span>
            </button>
          ) : (
            <div />
          )}
          <span className="text-white/80 text-xs">{cfg.subtitle}</span>
          <div className="w-10" />
        </div>
        <div className="h-1.5 bg-white/30 rounded-full overflow-hidden mb-3">
          <div
            className="h-full bg-white rounded-full transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>
        <h2 className="text-white font-medium text-lg">{cfg.title}</h2>
      </div>

      <div className={`${cfg.lightBg} p-4`}>
        <div className={`grid ${cfg.cols} gap-3`}>
          {cfg.options.map((opt) => {
            const isSelected = currentValue === opt.label;
            return (
              <button
                key={opt.label}
                onClick={() => onSelect(opt.label)}
                className={`flex flex-col items-center p-4 rounded-2xl transition-all active:scale-95 ${
                  isSelected
                    ? `${cfg.cardBg} shadow-md scale-105`
                    : "bg-white hover:bg-white/80 shadow-sm"
                }`}
              >
                <span className="text-3xl mb-1.5">{opt.emoji}</span>
                <span className={`text-xs font-medium ${isSelected ? "text-white" : "text-gray-700"}`}>
                  {opt.label}
                </span>
              </button>
            );
          })}
        </div>

        {step === "soreness" && soreness && (
          <button
            onClick={onSubmit}
            className="mt-4 w-full bg-lavender-500 hover:bg-lavender-600 text-white py-3.5 rounded-2xl transition-colors font-medium"
          >
            Complete Check-In ✓
          </button>
        )}
      </div>
    </div>
  );
}

// ── Complete Check-In Summary ─────────────────────────────────────
function CheckInComplete({
  feeling,
  energy,
  soreness,
}: {
  feeling: string;
  energy: string;
  soreness: string;
}) {
  return (
    <div className="mb-5 bg-lavender-50 rounded-3xl p-5 border border-lavender-200">
      <div className="flex items-center gap-3 mb-3">
        <div className="w-10 h-10 bg-lavender-500 rounded-full flex items-center justify-center flex-shrink-0">
          <Check className="w-5 h-5 text-white" strokeWidth={3} />
        </div>
        <div>
          <p className="font-medium text-gray-800">Check-In Complete!</p>
          <p className="text-xs text-gray-500">Today's insights are personalized</p>
        </div>
      </div>
      <div className="flex gap-2">
        {[
          { label: "Feeling", value: feeling, bg: "bg-lavender-100", text: "text-lavender-700" },
          { label: "Energy", value: energy, bg: "bg-amber-100", text: "text-amber-700" },
          { label: "Soreness", value: soreness, bg: "bg-emerald-100", text: "text-emerald-700" },
        ].map((item) => (
          <div key={item.label} className={`flex-1 ${item.bg} rounded-xl p-2.5 text-center`}>
            <p className="text-xs text-gray-500 mb-0.5">{item.label}</p>
            <p className={`text-xs font-medium ${item.text}`}>{item.value}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Recommendation Card ───────────────────────────────────────────
type FeedbackState = "liked" | "disliked" | null;

interface DisplayRec {
  id: string;
  title: string;
  duration: string;
  badge: string;
  badgeBg: string;
  badgeText: string;
  Icon: React.ComponentType<{ className?: string }>;
  iconBg: string;
  iconColor: string;
  workoutType: string;
}

function RecommendationCard({
  rec,
  feedback,
  onFeedback,
}: {
  rec: DisplayRec;
  feedback: FeedbackState;
  onFeedback: (v: FeedbackState) => void;
}) {
  const { Icon } = rec;
  return (
    <div className="bg-white rounded-2xl border border-lavender-100 shadow-sm overflow-hidden mb-3">
      <div className="flex">
        <div className="w-1 bg-lavender-400 flex-shrink-0 rounded-l-2xl" />
        <div className="flex-1 p-4">
          <div className="flex items-center gap-3 mb-3">
            <div className={`w-11 h-11 ${rec.iconBg} rounded-xl flex items-center justify-center flex-shrink-0`}>
              <Icon className={`w-5 h-5 ${rec.iconColor}`} />
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="font-medium text-gray-900 mb-0.5">{rec.title}</h3>
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-500">{rec.duration}</span>
                <span className="text-gray-300">·</span>
                <span className={`text-xs px-2 py-0.5 rounded-full ${rec.badgeBg} ${rec.badgeText} font-medium`}>
                  {rec.badge}
                </span>
              </div>
            </div>
          </div>

          <div className="flex gap-2">
            <button
              onClick={() => onFeedback(feedback === "liked" ? null : "liked")}
              className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-xl transition-all text-sm font-medium ${
                feedback === "liked"
                  ? "bg-gray-200 text-gray-700 shadow-sm"
                  : "bg-gray-50 text-gray-500 hover:bg-gray-100 border border-gray-200"
              }`}
            >
              <ThumbsUp className="w-4 h-4" />
              <span>{feedback === "liked" ? "Liked!" : "Like"}</span>
            </button>
            <button
              onClick={() => onFeedback(feedback === "disliked" ? null : "disliked")}
              className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-xl transition-all text-sm font-medium ${
                feedback === "disliked"
                  ? "bg-coral-400 text-white shadow-sm"
                  : "bg-gray-50 text-gray-500 hover:bg-gray-100 border border-gray-200"
              }`}
            >
              <ThumbsDown className="w-4 h-4" />
              <span>{feedback === "disliked" ? "Noted" : "Dislike"}</span>
            </button>
          </div>

          {feedback === "disliked" && (
            <p className="text-xs text-gray-400 text-center mt-2">
              We'll show you fewer workouts like this 🙏
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Static fallback recommendations ──────────────────────────────
const FALLBACK_RECS: DisplayRec[] = [
  {
    id: "hiit",
    title: "HIIT Circuit",
    duration: "25 min",
    badge: "High Intensity",
    badgeBg: "bg-coral-100",
    badgeText: "text-coral-700",
    Icon: Dumbbell,
    iconBg: "bg-coral-100",
    iconColor: "text-coral-600",
    workoutType: "hiit",
  },
  {
    id: "swimming",
    title: "Lap Swimming",
    duration: "40 min",
    badge: "Full Body",
    badgeBg: "bg-blue-100",
    badgeText: "text-blue-700",
    Icon: Wind,
    iconBg: "bg-blue-100",
    iconColor: "text-blue-600",
    workoutType: "swimming",
  },
  {
    id: "strength",
    title: "Strength Training",
    duration: "45 min",
    badge: "Muscle Build",
    badgeBg: "bg-lavender-100",
    badgeText: "text-lavender-700",
    Icon: Dumbbell,
    iconBg: "bg-lavender-100",
    iconColor: "text-lavender-600",
    workoutType: "strength training",
  },
  {
    id: "cycling",
    title: "Cycling",
    duration: "35 min",
    badge: "Cardio",
    badgeBg: "bg-emerald-100",
    badgeText: "text-emerald-700",
    Icon: Footprints,
    iconBg: "bg-emerald-100",
    iconColor: "text-emerald-600",
    workoutType: "cycling",
  },
  {
    id: "yoga",
    title: "Power Yoga",
    duration: "30 min",
    badge: "Flexibility",
    badgeBg: "bg-amber-100",
    badgeText: "text-amber-700",
    Icon: Wind,
    iconBg: "bg-amber-100",
    iconColor: "text-amber-600",
    workoutType: "yoga",
  },
];

// ── Energy/soreness label → API number mappings ───────────────────
const ENERGY_MAP: Record<string, number> = { High: 5, Medium: 3, Low: 1 };
const SORENESS_MAP: Record<string, number> = { None: 1, "A Little": 2, Moderate: 3, "Very Sore": 5 };

// ── Main Home Component ───────────────────────────────────────────
export function Home() {
  const [checkInStep, setCheckInStep] = useState<CheckInStep>("feeling");
  const [feeling, setFeeling] = useState("");
  const [energy, setEnergy] = useState("");
  const [soreness, setSoreness] = useState("");
  const [feedback, setFeedback] = useState<Record<string, FeedbackState>>({});

  const [apiData, setApiData] = useState<SuggestionsResponse | null>(null);
  const [baseStreak, setBaseStreak] = useState(0);
  const { dayOffset } = useAppContext();

  const today = new Date();
  today.setDate(today.getDate() + dayOffset);
  const dateString = today.toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
  });

  const stepIndex = STEPS.indexOf(checkInStep as (typeof STEPS)[number]);

  const fetchSuggestions = useCallback(async () => {
    try {
      const data = await api.getSuggestions(USER_ID);
      setApiData(data);
    } catch (e) {
      console.error("Failed to fetch suggestions:", e);
    }
  }, []);

  useEffect(() => {
    api.getUser(USER_ID).then((u) => setBaseStreak(u.checkin_streak)).catch(() => {});
    fetchSuggestions();
  }, [fetchSuggestions]);

  const handleSelect = (val: string) => {
    if (checkInStep === "feeling") {
      setFeeling(val);
      setTimeout(() => setCheckInStep("energy"), 320);
    } else if (checkInStep === "energy") {
      setEnergy(val);
      setTimeout(() => setCheckInStep("soreness"), 320);
    } else if (checkInStep === "soreness") {
      setSoreness(val);
    }
  };

  const handleBack = () => {
    if (checkInStep === "energy") setCheckInStep("feeling");
    else if (checkInStep === "soreness") setCheckInStep("energy");
  };

  const handleSubmit = async () => {
    setCheckInStep("complete");
    try {
      await api.submitCheckin(USER_ID, {
        energy: ENERGY_MAP[energy] ?? 3,
        soreness: SORENESS_MAP[soreness] ?? 1,
        mood: feeling.toLowerCase(),
      });
      // Re-fetch suggestions personalized with today's check-in
      fetchSuggestions();
    } catch (e) {
      console.error("Failed to submit check-in:", e);
    }
  };

  const handleFeedback = async (recId: string, workoutType: string, v: FeedbackState) => {
    setFeedback((prev) => ({ ...prev, [recId]: v }));
    if (apiData && v !== null) {
      try {
        await api.submitFeedback(apiData.suggestion_id, v === "liked", workoutType);
      } catch (e) {
        console.error("Failed to submit feedback:", e);
      }
    }
  };

  const isComplete = checkInStep === "complete";
  const streak = apiData?.checkin_streak ?? baseStreak;

  // Build display recommendations from API or fall back to static list
  const displayRecs: DisplayRec[] = apiData?.suggestions.map((s, i) => {
    const style = getWorkoutStyle(s.type);
    return {
      id: `${s.type}-${i}`,
      title: toTitleCase(s.type),
      duration: `${s.duration_mins} min`,
      badge: style.badge,
      badgeBg: style.badgeBg,
      badgeText: style.badgeText,
      Icon: style.Icon,
      iconBg: style.iconBg,
      iconColor: style.iconColor,
      workoutType: s.type,
    };
  }) ?? FALLBACK_RECS;

  return (
    <div className="p-5 max-w-md mx-auto">
      {/* Header */}
      <div className="mb-5">
        <p className="text-gray-400 text-sm mb-1">{dateString}</p>
        <h1 className="text-3xl text-gray-900">Home</h1>
      </div>

      {/* Streak */}
      <StreakCard complete={isComplete} streak={streak} />

      {/* Check-In */}
      {!isComplete ? (
        <CheckInCard
          step={checkInStep}
          feeling={feeling}
          energy={energy}
          soreness={soreness}
          onSelect={handleSelect}
          onBack={handleBack}
          onSubmit={handleSubmit}
          stepIndex={stepIndex >= 0 ? stepIndex : 0}
        />
      ) : (
        <CheckInComplete feeling={feeling} energy={energy} soreness={soreness} />
      )}

      {/* Recommendations */}
      <div className="mb-2">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-7 h-7 bg-lavender-100 rounded-full flex items-center justify-center">
            <Sparkles className="w-3.5 h-3.5 text-lavender-600" />
          </div>
          <div>
            <h2 className="font-medium text-gray-900">Based on your estimated insights</h2>
            {isComplete && (
              <p className="text-xs text-lavender-500">Personalized for today ✓</p>
            )}
          </div>
        </div>

        {displayRecs.map((rec) => (
          <RecommendationCard
            key={rec.id}
            rec={rec}
            feedback={feedback[rec.id] ?? null}
            onFeedback={(v) => handleFeedback(rec.id, rec.workoutType, v)}
          />
        ))}
      </div>
    </div>
  );
}
