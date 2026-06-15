import { Status } from "./theme";

export type Rule = { n: number; label: string; status: Status; note?: string };

export type SceneSpec =
  | { kind: "intro" }
  | { kind: "outro" }
  | {
      kind: "beat";
      subject: string;
      program: string;
      command: string;
      rules: Rule[];
      coverage: string;
      verdict: { label: string; status: Status };
      referral?: string;
      missing?: string;
    };

const allPass: Rule[] = [
  { n: 1, label: "citizenship", status: "pass" },
  { n: 2, label: "academic_merit", status: "pass" },
  { n: 3, label: "financial_need", status: "pass" },
  { n: 4, label: "priority_course", status: "pass" },
  { n: 5, label: "year_level", status: "pass" },
  { n: 6, label: "no_concurrent", status: "pass" },
];

export const scenes: Record<string, SceneSpec> = {
  intro: { kind: "intro" },

  beat1: {
    kind: "beat",
    subject: "Liza",
    program: "DOST-SEI Scholarship",
    command: "$ batayan ask --applicant liza.json",
    rules: [
      { n: 1, label: "citizenship", status: "pass" },
      { n: 2, label: "academic_merit", status: "pass", note: '"GWA of at least 90…"  as of 2026-01-15' },
      { n: 3, label: "financial_need", status: "pass" },
      { n: 4, label: "priority_course", status: "pass" },
      { n: 5, label: "year_level", status: "pass" },
      { n: 6, label: "no_concurrent", status: "pass" },
    ],
    coverage: "6 / 6 grounded & checked",
    verdict: { label: "ELIGIBLE", status: "pass" },
  },

  beat2: {
    kind: "beat",
    subject: "Mateo",
    program: "DOST-SEI Scholarship",
    command: "$ batayan ask --applicant mateo.json",
    rules: [
      { n: 1, label: "citizenship", status: "pass" },
      { n: 2, label: "academic_merit", status: "pass" },
      { n: 3, label: "financial_need", status: "fail", note: "income 650k > 400k cap   fix: corrected income statement" },
      { n: 4, label: "priority_course", status: "pass" },
      { n: 5, label: "year_level", status: "pass" },
      { n: 6, label: "no_concurrent", status: "pass" },
    ],
    coverage: "6 / 6 grounded & checked",
    verdict: { label: "INELIGIBLE", status: "fail" },
    referral: "→ referral: CHED Tulong-Dunong Grant  —  ELIGIBLE",
  },

  beat3: {
    kind: "beat",
    subject: "Aisha",
    program: "DOST-SEI Scholarship",
    command: "$ batayan ask --applicant aisha.json",
    rules: [
      { n: 1, label: "citizenship", status: "pass" },
      { n: 2, label: "academic_merit", status: "pass" },
      { n: 3, label: "financial_need", status: "abstain", note: "applicant did not provide household_income_annual" },
      { n: 4, label: "priority_course", status: "pass" },
      { n: 5, label: "year_level", status: "pass" },
      { n: 6, label: "no_concurrent", status: "pass" },
    ],
    coverage: "5 / 6 — refuses to guess",
    verdict: { label: "INSUFFICIENT_EVIDENCE", status: "abstain" },
    missing: "still needed: household_income_annual",
  },

  outro: { kind: "outro" },
};

void allPass;
