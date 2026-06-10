import type {
  AssetType, ControlType, TechniqueType, ScenarioSummary, Topology,
  RunConfig, RunSummary, SimEvent, ReportContent, Dashboard, RoleInfo, WorkflowDef,
  LiveSessionSummary, LiveMission, LabStatus, LabToolRegistry,
} from "./types";

async function get<T>(url: string): Promise<T> {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${r.status} ${url}`);
  return r.json();
}
async function post<T>(url: string, body: unknown): Promise<T> {
  const r = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`${r.status} ${url}: ${await r.text()}`);
  return r.json();
}

export const api = {
  assets: () => get<AssetType[]>("/api/catalog/assets"),
  controls: () => get<ControlType[]>("/api/catalog/controls"),
  techniques: () => get<TechniqueType[]>("/api/catalog/techniques"),
  roles: () => get<RoleInfo[]>("/api/catalog/roles"),
  workflows: () => get<WorkflowDef[]>("/api/catalog/workflows"),

  scenarios: () => get<ScenarioSummary[]>("/api/scenarios"),
  scenario: (id: string) => get<any>(`/api/scenarios/${id}`),
  topology: (id: string) => get<Topology>(`/api/scenarios/${id}/topology`),

  launch: (body: { scenario_id: string; environment_spec?: Topology; config?: RunConfig; operator?: string }) =>
    post<RunSummary>("/api/runs", body),
  runs: (limit = 20) => get<RunSummary[]>(`/api/runs?limit=${limit}`),
  run: (id: string) => get<RunSummary>(`/api/runs/${id}`),
  runEvents: (id: string) => get<SimEvent[]>(`/api/runs/${id}/events`),
  report: (id: string) => get<ReportContent>(`/api/runs/${id}/report`),

  dashboard: () => get<Dashboard>("/api/dashboard"),
  leaderboard: () => get<any[]>("/api/leaderboard"),

  // ---- Live multiplayer ----
  liveSessions: () => get<LiveSessionSummary[]>("/api/live/sessions"),
  liveMissions: () => get<LiveMission[]>("/api/live/missions"),
  liveSession: (id: string) => get<LiveSessionSummary & { players: any[] }>(`/api/live/sessions/${id}`),
  createLiveSession: (body: { host_name: string; mission_id?: string; scenario_id?: string }) =>
    post<{ session_id: string; player_id: string; scenario_name: string; status: string }>("/api/live/sessions", body),
  joinLiveSession: (id: string, body: { name: string }) =>
    post<{ session_id: string; player_id: string; scenario_name: string; status: string }>(`/api/live/sessions/${id}/join`, body),

  // ---- Guided scenarios (the 3 demo walkthroughs: W1/R5/C5) ----
  guidedScenarios: () => get<any[]>("/api/live/guided"),
  guidedScenario: (id: string) => get<any>(`/api/live/guided/${id}`),
  createGuidedSession: (body: { host_name: string; scenario_id: string }) =>
    post<{ session_id: string; player_id: string; scenario_id: string; scenario_name: string; status: string }>(
      "/api/live/guided/sessions", body),

  // ---- Live-fire lab (real VMs + real tools) ----
  labStatus: () => get<LabStatus>("/api/lab/status"),
  labTools: () => get<LabToolRegistry>("/api/lab/tools"),
  labUp: () => post<{ ok: boolean; detail: string; command: string }>("/api/lab/up", {}),
  labDown: () => post<{ ok: boolean; detail: string; command: string }>("/api/lab/down", {}),
};
