import { useState, useEffect } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  ResponsiveContainer,
} from "recharts";
import { ChevronLeft, ChevronRight, CalendarDays } from "lucide-react";
import { api } from "@/api/client";

const USER_ID = 1;

// ── Fallback cycle reference (used until API responds) ─────────────
const DEFAULT_CYCLE_START = new Date(2026, 2, 28); // March 28, 2026
const DEFAULT_CYCLE_LENGTH = 28;

type Phase = "menstrual" | "follicular" | "ovulation" | "luteal";

// Normalize backend phase names ("ovulatory" → "ovulation")
function normalizePhase(phase: string): Phase {
  if (phase === "ovulatory") return "ovulation";
  if (phase === "menstrual" || phase === "follicular" || phase === "luteal") return phase;
  return "luteal";
}

function getPhaseForDate(
  year: number,
  month: number,
  day: number,
  cycleStart: Date,
  cycleLength: number
): Phase {
  const date = new Date(year, month, day);
  const diffDays = Math.floor(
    (date.getTime() - cycleStart.getTime()) / (1000 * 60 * 60 * 24)
  );
  const cycleDay =
    ((diffDays % cycleLength) + cycleLength) % cycleLength + 1; // 1-based

  const menstrualEnd = 5;
  const follicularEnd = Math.round(cycleLength * 0.46); // ~day 13 for 28-day cycle
  const ovulationDay = Math.round(cycleLength * 0.5);  // ~day 14

  if (cycleDay >= 1 && cycleDay <= menstrualEnd) return "menstrual";
  if (cycleDay >= menstrualEnd + 1 && cycleDay <= follicularEnd) return "follicular";
  if (cycleDay === ovulationDay) return "ovulation";
  return "luteal";
}

// ── Phase visual styles ────────────────────────────────────────────
const phaseStyles: Record<
  Phase,
  { dayCellBg: string; dayText: string; legendBg: string; dot: string }
> = {
  menstrual: {
    dayCellBg: "bg-coral-200",
    dayText: "text-coral-800",
    legendBg: "bg-coral-200",
    dot: "bg-coral-400",
  },
  follicular: {
    dayCellBg: "bg-emerald-100",
    dayText: "text-emerald-800",
    legendBg: "bg-emerald-100",
    dot: "bg-emerald-400",
  },
  ovulation: {
    dayCellBg: "bg-lavender-300",
    dayText: "text-lavender-900",
    legendBg: "bg-lavender-300",
    dot: "bg-lavender-500",
  },
  luteal: {
    dayCellBg: "bg-amber-100",
    dayText: "text-amber-800",
    legendBg: "bg-amber-100",
    dot: "bg-amber-400",
  },
};

// ── Phase info cards ───────────────────────────────────────────────
const phaseInfo: Record<
  Phase,
  {
    emoji: string;
    title: string;
    cycleDay: string;
    cardBg: string;
    cardBorder: string;
    titleColor: string;
    desc: string;
    tips: string[];
    estimatedEnergy: number;
  }
> = {
  menstrual: {
    emoji: "🌸",
    title: "Menstrual Phase",
    cycleDay: "Days 1–5",
    cardBg: "bg-coral-50",
    cardBorder: "border-coral-200",
    titleColor: "text-coral-600",
    desc: "Your body is shedding its uterine lining. Rest is key — prioritize gentle movement, stay hydrated, and nourish yourself with iron-rich foods.",
    tips: ["Gentle yoga or walking", "Iron-rich foods (leafy greens, lentils)", "Extra rest & quality sleep"],
    estimatedEnergy: 3,
  },
  follicular: {
    emoji: "🌱",
    title: "Follicular Phase",
    cycleDay: "Days 6–13",
    cardBg: "bg-emerald-50",
    cardBorder: "border-emerald-200",
    titleColor: "text-emerald-700",
    desc: "Estrogen is rising and energy is building. A great time to try new workouts, set ambitious goals, and embrace creativity.",
    tips: ["Try higher-intensity workouts", "Set new fitness goals", "Leverage creativity & focus"],
    estimatedEnergy: 7,
  },
  ovulation: {
    emoji: "✨",
    title: "Ovulation Phase",
    cycleDay: "Day 14",
    cardBg: "bg-lavender-50",
    cardBorder: "border-lavender-200",
    titleColor: "text-lavender-600",
    desc: "Peak energy, strength, and confidence! You're at your most powerful — perfect for HIIT, heavy lifting, and social activities.",
    tips: ["HIIT or strength training", "Leverage peak performance", "Be mindful of joint laxity"],
    estimatedEnergy: 9,
  },
  luteal: {
    emoji: "🌙",
    title: "Luteal Phase",
    cycleDay: "Days 15–28",
    cardBg: "bg-amber-50",
    cardBorder: "border-amber-200",
    titleColor: "text-amber-700",
    desc: "Progesterone rises and energy gradually decreases. Focus on moderate exercise, self-care, and easing pre-menstrual symptoms.",
    tips: ["Moderate cardio or yoga", "Reduce caffeine & sugar", "Prioritize sleep & stress relief"],
    estimatedEnergy: 4,
  },
};

// ── Weekly Phase Overview ──────────────────────────────────────────
function WeeklyPhaseOverview({
  cycleStart,
  cycleLength,
}: {
  cycleStart: Date;
  cycleLength: number;
}) {
  const today = new Date();
  const dow = today.getDay();
  const monday = new Date(today);
  monday.setDate(today.getDate() - ((dow + 6) % 7));

  const days = Array.from({ length: 7 }, (_, i) => {
    const d = new Date(monday);
    d.setDate(monday.getDate() + i);
    return d;
  });
  const labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

  return (
    <div className="bg-white rounded-3xl p-5 border border-lavender-100 shadow-sm">
      <div className="flex items-center gap-2 mb-4">
        <CalendarDays className="w-4 h-4 text-lavender-500" />
        <h3 className="font-medium text-gray-800">Weekly Overview by Phase</h3>
      </div>
      <div className="flex gap-1.5">
        {days.map((d, i) => {
          const phase = getPhaseForDate(d.getFullYear(), d.getMonth(), d.getDate(), cycleStart, cycleLength);
          const styles = phaseStyles[phase];
          const isToday = d.toDateString() === today.toDateString();
          return (
            <div key={i} className="flex flex-col items-center gap-1 flex-1">
              <span className={`text-xs ${isToday ? "text-lavender-600 font-medium" : "text-gray-400"}`}>
                {labels[i]}
              </span>
              <div
                className={`w-full aspect-square rounded-xl flex items-center justify-center ${styles.dayCellBg} ${
                  isToday ? "ring-2 ring-lavender-500 ring-offset-1" : ""
                }`}
              >
                <span className={`text-xs font-medium ${styles.dayText}`}>{d.getDate()}</span>
              </div>
              <span className={`text-xs font-medium ${styles.dayText}`}>
                {phase === "menstrual" ? "M" : phase === "follicular" ? "F" : phase === "ovulation" ? "O" : "L"}
              </span>
            </div>
          );
        })}
      </div>
      <div className="mt-3 pt-3 border-t border-gray-100 grid grid-cols-2 gap-y-1.5 gap-x-3">
        {(["menstrual", "follicular", "ovulation", "luteal"] as Phase[]).map((p) => (
          <div key={p} className="flex items-center gap-1.5">
            <div className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${phaseStyles[p].legendBg} border border-gray-200`} />
            <span className="text-xs text-gray-500 capitalize">{p}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Calendar component ─────────────────────────────────────────────
function CalendarView({
  cycleStart,
  cycleLength,
}: {
  cycleStart: Date;
  cycleLength: number;
}) {
  const today = new Date();
  const [viewYear, setViewYear] = useState(today.getFullYear());
  const [viewMonth, setViewMonth] = useState(today.getMonth());

  const prevMonth = () => {
    if (viewMonth === 0) { setViewMonth(11); setViewYear((y) => y - 1); }
    else setViewMonth((m) => m - 1);
  };
  const nextMonth = () => {
    if (viewMonth === 11) { setViewMonth(0); setViewYear((y) => y + 1); }
    else setViewMonth((m) => m + 1);
  };

  const monthLabel = new Date(viewYear, viewMonth, 1).toLocaleDateString("en-US", {
    month: "long",
    year: "numeric",
  });

  const firstWeekday = new Date(viewYear, viewMonth, 1).getDay();
  const daysInMonth = new Date(viewYear, viewMonth + 1, 0).getDate();

  const cells: (number | null)[] = [
    ...Array(firstWeekday).fill(null),
    ...Array.from({ length: daysInMonth }, (_, i) => i + 1),
  ];
  while (cells.length % 7 !== 0) cells.push(null);

  const weeks: (number | null)[][] = [];
  for (let i = 0; i < cells.length; i += 7) weeks.push(cells.slice(i, i + 7));

  const todayPhase = getPhaseForDate(today.getFullYear(), today.getMonth(), today.getDate(), cycleStart, cycleLength);
  const todayInfo = phaseInfo[todayPhase];

  return (
    <div className="space-y-4">
      {/* Calendar Card */}
      <div className="bg-white rounded-3xl p-5 shadow-sm border border-gray-200">
        <div className="flex items-center justify-between mb-4">
          <button
            onClick={prevMonth}
            className="w-8 h-8 rounded-full bg-lavender-100 hover:bg-lavender-200 flex items-center justify-center transition-colors"
          >
            <ChevronLeft className="w-4 h-4 text-lavender-600" />
          </button>
          <h3 className="font-medium text-gray-800">{monthLabel}</h3>
          <button
            onClick={nextMonth}
            className="w-8 h-8 rounded-full bg-lavender-100 hover:bg-lavender-200 flex items-center justify-center transition-colors"
          >
            <ChevronRight className="w-4 h-4 text-lavender-600" />
          </button>
        </div>

        <div className="grid grid-cols-7 mb-1">
          {["S", "M", "T", "W", "T", "F", "S"].map((d, i) => (
            <div key={i} className="text-center text-xs text-gray-400 font-medium py-1">
              {d}
            </div>
          ))}
        </div>

        <div className="space-y-0.5">
          {weeks.map((week, wi) => (
            <div key={wi} className="grid grid-cols-7">
              {week.map((day, di) => {
                if (!day) return <div key={di} className="aspect-square" />;

                const phase = getPhaseForDate(viewYear, viewMonth, day, cycleStart, cycleLength);
                const styles = phaseStyles[phase];
                const isToday =
                  day === today.getDate() &&
                  viewMonth === today.getMonth() &&
                  viewYear === today.getFullYear();

                return (
                  <div key={di} className="aspect-square flex items-center justify-center p-0.5">
                    <div
                      className={`w-full h-full rounded-full flex items-center justify-center text-xs font-medium
                        ${styles.dayCellBg} ${styles.dayText}
                        ${isToday ? "ring-2 ring-offset-1 ring-lavender-500" : ""}
                      `}
                    >
                      {day}
                    </div>
                  </div>
                );
              })}
            </div>
          ))}
        </div>

        <div className="mt-4 pt-3 border-t border-gray-100 grid grid-cols-2 gap-y-2 gap-x-3">
          {(["menstrual", "follicular", "ovulation", "luteal"] as Phase[]).map((p) => (
            <div key={p} className="flex items-center gap-2">
              <div className={`w-3 h-3 rounded-full flex-shrink-0 ${phaseStyles[p].legendBg} border border-gray-200`} />
              <span className="text-xs text-gray-600 capitalize">{p}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Current-phase insight card */}
      <div className={`rounded-3xl p-5 border ${todayInfo.cardBg} ${todayInfo.cardBorder}`}>
        <div className="flex items-center gap-3 mb-3">
          <span className="text-3xl leading-none">{todayInfo.emoji}</span>
          <div>
            <p className={`font-semibold ${todayInfo.titleColor}`}>{todayInfo.title}</p>
            <p className="text-xs text-gray-500">Today · {todayInfo.cycleDay}</p>
          </div>
        </div>
        <p className="text-sm text-gray-700 leading-relaxed mb-3">{todayInfo.desc}</p>
        <div className="space-y-2">
          {todayInfo.tips.map((tip, i) => (
            <div key={i} className="flex items-start gap-2">
              <div className={`w-1.5 h-1.5 rounded-full flex-shrink-0 mt-1.5 ${phaseStyles[todayPhase].dot}`} />
              <p className="text-sm text-gray-600">{tip}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Main Insights component ────────────────────────────────────────
export function Insights() {
  const [activeTab, setActiveTab] = useState<"calendar" | "trends">("calendar");
  const [cycleStart, setCycleStart] = useState(DEFAULT_CYCLE_START);
  const [cycleLength, setCycleLength] = useState(DEFAULT_CYCLE_LENGTH);
  const [currentPhase, setCurrentPhase] = useState<Phase>("luteal");
  const [cycleDay, setCycleDay] = useState<number | null>(null);

  const today = new Date();
  const dateString = today.toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
  });

  useEffect(() => {
    api.getUser(USER_ID).then((user) => {
      if (user.cycle_length_avg) setCycleLength(user.cycle_length_avg);
      if (user.cycle_info) {
        const { last_period_start, phase, cycle_day } = user.cycle_info;
        if (last_period_start) {
          const [y, m, d] = last_period_start.split("-").map(Number);
          setCycleStart(new Date(y, m - 1, d));
        }
        if (phase) setCurrentPhase(normalizePhase(phase));
        if (cycle_day) setCycleDay(cycle_day);
      }
    }).catch((e) => console.error("Failed to fetch user:", e));
  }, []);

  const energyData = [
    { day: 1, energy: 3 },
    { day: 5, energy: 5 },
    { day: 9, energy: 7 },
    { day: 13, energy: 8 },
    { day: 17, energy: 6 },
    { day: 21, energy: 4 },
    { day: 25, energy: 3 },
  ];

  const todayInfo = phaseInfo[currentPhase];
  const estimatedEnergy = todayInfo.estimatedEnergy;

  return (
    <div className="max-w-md mx-auto">
      {/* Header */}
      <div className="p-5 pb-3">
        <p className="text-gray-500 text-sm mb-1">{dateString}</p>
        <h1 className="text-3xl">Insights</h1>
      </div>

      {/* Tab Navigation */}
      <div className="px-5 mb-4">
        <div className="flex gap-2 border-b border-gray-200">
          {([
            { key: "calendar", label: "Phases" },
            { key: "trends",   label: "Energy" },
          ] as const).map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setActiveTab(key)}
              className={`px-4 py-2 -mb-px text-sm transition-colors ${
                activeTab === key
                  ? "border-b-2 border-lavender-500 text-lavender-600 font-medium"
                  : "text-gray-500 hover:text-gray-700"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {activeTab === "calendar" ? (
        <div className="px-5 pb-6 space-y-4">
          <WeeklyPhaseOverview cycleStart={cycleStart} cycleLength={cycleLength} />
          <CalendarView cycleStart={cycleStart} cycleLength={cycleLength} />
        </div>
      ) : (
        <div className="px-5 pb-6 space-y-4">
          {/* Today's Estimated Energy */}
          <div className="bg-lavender-500 rounded-3xl p-5 text-white">
            <p className="text-lavender-200 text-xs mb-1">Today's Estimated Energy</p>
            <div className="flex items-end gap-3 mb-3">
              <span className="text-5xl font-medium leading-none">{estimatedEnergy}</span>
              <span className="text-lavender-200 text-sm mb-1">/ 10</span>
            </div>
            <div className="h-2 bg-white/20 rounded-full overflow-hidden mb-3">
              <div className="h-full bg-white rounded-full" style={{ width: `${estimatedEnergy * 10}%` }} />
            </div>
            <p className="text-lavender-100 text-sm">
              {cycleDay ? (
                <>
                  You're on <span className="text-white font-medium">Day {cycleDay}</span> in your{" "}
                  <span className="text-white font-medium">{todayInfo.title}</span> — {todayInfo.desc.split(".")[0].toLowerCase()}.
                </>
              ) : (
                <>
                  You're in your <span className="text-white font-medium">{todayInfo.title}</span> — {todayInfo.tips[0].toLowerCase()}.
                </>
              )}
            </p>
          </div>

          {/* Energy Trends Chart */}
          <div className="bg-white rounded-3xl p-5 shadow-sm border border-gray-200">
            <h2 className="text-xl mb-1">Energy Trends</h2>
            <p className="text-xs text-gray-400 mb-4">By cycle day — last 28 days</p>
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={energyData}>
                <defs>
                  <linearGradient id="energyGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="#c084fc" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#c084fc" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
                <XAxis
                  dataKey="day"
                  label={{ value: "cycle day", position: "insideBottom", offset: -5 }}
                  tick={{ fontSize: 11 }}
                  stroke="#d1d5db"
                />
                <YAxis domain={[0, 10]} tick={{ fontSize: 11 }} stroke="#d1d5db" />
                <Area
                  type="monotone"
                  dataKey="energy"
                  stroke="#a855f7"
                  strokeWidth={2.5}
                  fill="url(#energyGradient)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          {/* Trend descriptions */}
          <div className="bg-white rounded-3xl p-5 shadow-sm border border-gray-200 space-y-3">
            <h3 className="font-medium text-gray-800">Trend Summary</h3>
            {[
              { dot: "bg-lavender-500", text: "Energy peaked mid-cycle during ovulation — typical and healthy for your pattern." },
              { dot: "bg-amber-400",    text: `Currently in ${todayInfo.title.toLowerCase()} — ${todayInfo.tips[2]?.toLowerCase() ?? "focus on recovery"}.` },
              { dot: "bg-emerald-400",  text: "Your cycle consistency has been excellent over the past 3 months." },
            ].map((item, i) => (
              <div key={i} className="flex items-start gap-3">
                <div className={`w-2 h-2 rounded-full flex-shrink-0 mt-1.5 ${item.dot}`} />
                <p className="text-sm text-gray-700 leading-relaxed">{item.text}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
