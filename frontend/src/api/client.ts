const API_BASE = "/api";

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export interface CycleInfo {
  cycle_day: number;
  phase: string;
  days_until_period: number;
  cycle_length_avg: number;
  last_period_start: string;
}

export interface User {
  id: number;
  name: string;
  fitness_level: string;
  cycle_length_avg: number;
  workout_preferences?: { likes: string[]; dislikes: string[] };
  profile_summary?: string;
  cycle_info?: CycleInfo;
  checkin_streak: number;
}

export interface Suggestion {
  rank: number;
  type: string;
  description: string;
  duration_mins: number;
  intensity: string;
  specific_suggestion: string;
  reasoning: Record<string, string>;
}

export interface SuggestionsResponse {
  suggestion_id: number;
  date: string;
  checkin_streak: number;
  cycle: CycleInfo;
  weather: {
    temp_f: number;
    condition: string;
    season: string;
    outdoor_friendly: boolean;
  };
  top: Suggestion;
  suggestions: Suggestion[];
}

export interface CheckinRequest {
  energy: number;
  soreness: number;
  mood: string;
  date?: string;
}

export const api = {
  getUser: (userId: number) => apiFetch<User>(`/users/${userId}`),

  submitCheckin: (userId: number, data: CheckinRequest) =>
    apiFetch<{ logged: boolean; date: string }>(`/users/${userId}/checkin`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  getSuggestions: (userId: number) =>
    apiFetch<SuggestionsResponse>(`/users/${userId}/suggest`),

  submitFeedback: (
    suggestionId: number,
    liked: boolean,
    workoutType?: string
  ) =>
    apiFetch<{ logged: boolean }>(`/suggestions/${suggestionId}/feedback`, {
      method: "POST",
      body: JSON.stringify({ liked, workout_type: workoutType }),
    }),

  logCycle: (userId: number, periodStartDate: string) =>
    apiFetch<{ logged: boolean; period_start_date: string }>(
      `/users/${userId}/cycle`,
      {
        method: "POST",
        body: JSON.stringify({ period_start_date: periodStartDate }),
      }
    ),
};
