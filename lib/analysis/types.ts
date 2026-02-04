/**
 * Stage Buddy V2 - Analysis Type Definitions
 * Matches the JSON structure produced by the S.T.A.R.R. orchestrator (report_generator.py).
 */

export interface PerformanceReport {
  performance_id: string;
  overall: {
    score: number;
    grade: string;
    summary: string;
  };
  pillars: PillarResult[];
  timeline: ReportTimeline;
  growth_plan: GrowthPlan;
}

export interface PillarResult {
  name: string;
  weight: number;
  score: number;
  subscores: Record<string, number>;
  feedback: string;
  icon: string;
  disabled?: boolean;  // True if this pillar is temporarily disabled
}

export interface ReportTimeline {
  duration_seconds: number;
  key_moments: KeyMoment[];
  engagement_curve: number[];
}

export interface KeyMoment {
  timestamp: number;
  type: string;
  description: string;
  coach_note: string;
}

export interface GrowthPlan {
  top_strengths: string[];
  focus_areas: string[];
}

export interface AnalysisStatus {
  status: 'pending' | 'running' | 'complete' | 'failed';
  error?: string;
  started_at?: string;
  completed_at?: string;
}
