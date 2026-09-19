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
}
