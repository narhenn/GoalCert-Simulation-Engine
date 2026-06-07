export interface AssetType {
  key: string; name: string; category: string; icon: string; description: string;
  default_zone: string; default_criticality: number; default_data_sensitivity: number;
  supported_controls: string[];
}
export interface ControlType {
  key: string; name: string; icon: string; description: string;
  default_scope: string; default_enabled: boolean; attaches_to: string[];
}
export interface TechniqueType {
  key: string; name: string; mitre: string; tactic: string; description: string;
  severity: string; detects: string[]; prevents: string[];
}
export interface ScenarioSummary {
  id: string; name: string; type: string; industry: string; badge: string; label: string;
  description: string; is_seed: boolean; phases: string[]; nominal_duration_min: number;
  difficulties: string[]; objectives: { red: string[]; blue: string[] };
  step_count: number; mitre_tactics: string[];
}
export interface AssetSpec {
  id: string; type: string; name?: string; role?: string; zone?: string;
  criticality?: number; data_sensitivity?: number; props?: Record<string, unknown>;
}
export interface ControlSpec {
  id: string; type: string; name?: string; enabled: boolean;
  scope?: string; targets?: string[];
}
export interface Topology { assets: AssetSpec[]; controls: ControlSpec[]; }

export interface RoleInfo { role: string; name: string; mission: string; description: string; }
export interface TaskEffect { kind: string; scope?: string | null; magnitude: number; }
export interface WorkflowStepDef {
  id: string; team: string; kind: string; label: string; description: string;
  phase_hint: string; irp_ref: string; default_enabled: boolean; removable: boolean;
  effects: TaskEffect[];
}
export interface WorkflowDef {
  actor: string; id: string; name: string; description: string; steps: WorkflowStepDef[];
}
export interface RoleTask { id: string; label: string; description?: string; status: string; }

export interface RunConfig {
  difficulty: "Easy" | "Medium" | "Hard" | "Expert";
  readiness: number; duration_min: number; industry?: string; seed?: number;
  focus_role?: string; phase_range?: [number, number] | null;
  workflow_config?: { enabled: Record<string, string[]> };
}
export interface RunSummary {
  id: string; scenario_id: string; scenario_name: string; operator?: string | null;
  status: string; duration_s: number; focus_role?: string; scores: Record<string, number>;
  kpis: Record<string, number>; summary: Record<string, any>; created_at: string;
  environment?: AssetNode[]; objectives?: { red: ObjStatus[]; blue: ObjStatus[] };
  workflows?: WorkflowDef[]; role_tasks?: Record<string, RoleTask[]>;
}
export interface ObjStatus { text: string; met: boolean; }
export interface AssetNode {
  id: string; type: string; name: string; role?: string | null; zone: string;
  criticality: number; security_state: string; health: string;
}
export interface SimEvent {
  seq: number; t: number; type: string; side: string; actor: string;
  phase?: string | null; severity: string; title: string; message: string;
  technique?: string | null; asset_id?: string | null; asset_label?: string | null;
  channel?: string | null; data: Record<string, any>;
}
export interface RoleScorecard {
  role: string; title: string; score: number; tasks_done: number; tasks_total: number;
  kpis: Record<string, string | number>; headline: string; tasks: RoleTask[];
}
export interface ReportContent {
  scenario_name: string; duration_min: number; focus_role?: string; exec_summary: string;
  role_scorecards?: RoleScorecard[];
  timeline: any[]; mitre_map: any[]; scorecard: Record<string, any>;
  regulatory_impact: { framework_name: string; message: string; deadline_hours: number; penalty?: string; on_time?: boolean; framework_id?: string }[];
  financial_impact: { estimate_low_usd: number; estimate_high_usd: number; drivers: string[] };
  recommendations: string[]; maturity_score: { score: number; band: string; breakdown?: Record<string, number> };
  corrective_actions: { priority: string; action: string }[];
  key_findings?: { strengths: string[]; weaknesses: string[]; critical_moment: string };
  attack_path?: { t: number; clock: string; technique: string; name: string; target_name: string; phase: string; severity: string; result: string; blocked_by?: string }[];
  per_asset?: { id: string; name: string; type: string; zone: string; criticality: number; data_sensitivity: number; initial_state: string; final_state: string; final_health: string; times_targeted: number; times_blocked: number; times_detected: number; contained: boolean; avg_dwell_s: number; detected_by: string[]; risk_score: number }[];
  control_effectiveness?: { type: string; name: string; detections: number; blocks: number; techniques_detected: string[]; techniques_blocked: string[]; avg_dwell_s: number; total_actions: number }[];
  dwell_analysis?: { overall: { mean_s: number; median_s: number; min_s: number; max_s: number; count: number }; by_asset: { asset: string; mean_s: number; count: number }[]; by_phase: { phase: string; mean_s: number; count: number }[]; worst: { asset: string | null; max_dwell_s: number } };
  zone_analysis?: { zone: string; assets_total: number; assets_compromised: number; assets_contained: number; assets_down: number; assets_safe: number; breach_pct: number; status: string; asset_names: string[] }[];
  credential_timeline?: { t: number; clock: string; scope: string; rank: number; technique: string; description: string; target: string }[];
}
export interface Dashboard {
  total_runs: number; total_scenarios: number; avg_blue_score: number; critical_findings: number;
  recent_runs: any[]; threat_coverage: { label: string; pct: number }[];
  readiness: Record<string, number>;
}
