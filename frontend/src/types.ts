export interface Company {
  id: string;
  name: string;
  domain: string | null;
}

export interface GateCheck {
  gate: string;
  passed: boolean;
  reason: string | null;
}

export interface Gates {
  status: "pass" | "fail" | "needs_sponsorship";
  checks: GateCheck[];
}

export interface MatchResult {
  match_id: string;
  job_id: string;
  company: string;
  title: string;
  location: string | null;
  score: number | null;
  components: Record<string, number>;
  gates: Gates;
  is_new?: boolean;
  dismissed?: boolean;
}

export interface ProfileBullet {
  id: string;
  experience_id: string | null;
  text: string;
  tags: string[];
}

export interface Profile {
  bullets: ProfileBullet[];
  [key: string]: unknown;
}

export interface TailoredBullet {
  id: string;
  source_bullet_id: string;
  text: string;
}

export interface TailoredSection {
  experience_id: string;
  bullets: TailoredBullet[];
}

export interface TailoredResumeContent {
  summary: string;
  sections: TailoredSection[];
  skills: { canonical: string }[];
}

export interface VerifiedClaim {
  claim: string;
  supported: boolean;
  reasoning: string;
}

export interface DocumentOut {
  id: string;
  match_id: string;
  kind: "resume" | "cover_letter";
  version: number;
  content: TailoredResumeContent;
  provenance_map: Record<string, string>;
  verify_report: { claims: VerifiedClaim[] } | null;
  rejected_bullets: { source_bullet_id: string; text: string; reason: string }[];
  status: "draft" | "approved";
  approved_bullet_ids: string[] | null;
}
