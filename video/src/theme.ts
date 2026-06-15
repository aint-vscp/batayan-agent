export const theme = {
  bg0: "#0e0918",
  bg1: "#080610",
  violet: "#7C5CFF",
  azure: "#38BDF8",
  green: "#34D399",
  red: "#F87171",
  amber: "#FBBF24",
  ink: "#F5F5FA",
  gray: "#A8A8C0",
  mute: "#6B6B85",
  card: "#11102a",
  cardBorder: "#26244a",
  fontSans:
    'Segoe UI, -apple-system, Helvetica, Arial, system-ui, sans-serif',
  fontMono: 'Consolas, "Cascadia Mono", "Courier New", monospace',
} as const;

export type Status = "pass" | "fail" | "abstain";

export const statusColor: Record<Status, string> = {
  pass: theme.green,
  fail: theme.red,
  abstain: theme.amber,
};

export const statusLabel: Record<Status, string> = {
  pass: "PASS",
  fail: "FAIL",
  abstain: "NEEDS EVIDENCE",
};
