import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { theme, statusColor, statusLabel, Status } from "../theme";
import { fadeUp, fadeIn } from "../anim";
import { Chip } from "./Chip";
import type { SceneSpec } from "../scenes";

type Beat = Extract<SceneSpec, { kind: "beat" }>;

const Row: React.FC<{ rule: Beat["rules"][number]; delay: number }> = ({ rule, delay }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = fadeUp(frame, fps, delay, 18, 16);
  const color = statusColor[rule.status as Status];
  return (
    <div style={{ ...s, marginBottom: rule.note ? 4 : 12 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ fontFamily: theme.fontMono, fontSize: 27, color: theme.ink }}>
          <span style={{ color: theme.mute }}>[{rule.n}]</span> {rule.label}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ width: 12, height: 12, borderRadius: 999, background: color }} />
          <div style={{ fontFamily: theme.fontMono, fontSize: 22, fontWeight: 700, color }}>
            {statusLabel[rule.status as Status]}
          </div>
        </div>
      </div>
      {rule.note ? (
        <div style={{ fontFamily: theme.fontMono, fontSize: 18, color: theme.mute, paddingLeft: 52, marginTop: 4, marginBottom: 12 }}>
          {rule.note}
        </div>
      ) : null}
    </div>
  );
};

export const Ledger: React.FC<{ spec: Beat }> = ({ spec }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const rowStart = 24;
  const rowStagger = 9;
  const lastRow = rowStart + (spec.rules.length - 1) * rowStagger;
  const verdictDelay = lastRow + 22;
  const extraDelay = verdictDelay + 18;

  return (
    <div
      style={{
        width: 1240,
        background: theme.card,
        border: `2px solid ${theme.cardBorder}`,
        borderRadius: 22,
        padding: "30px 40px 36px",
        boxShadow: "0 30px 80px rgba(0,0,0,0.45)",
        ...fadeUp(frame, fps, 0, 30, 18),
      }}
    >
      {/* header */}
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 18 }}>
        {["#ff5f56", "#ffbd2e", "#27c93f"].map((c) => (
          <div key={c} style={{ width: 14, height: 14, borderRadius: 999, background: c }} />
        ))}
        <div style={{ fontFamily: theme.fontMono, fontSize: 20, color: theme.mute, marginLeft: 10 }}>
          batayan — evidence ledger
        </div>
      </div>
      <div style={{ fontFamily: theme.fontMono, fontSize: 22, color: theme.azure, marginBottom: 8, ...fadeIn(frame, fps, 8) }}>
        {spec.command}
      </div>
      <div style={{ fontFamily: theme.fontMono, fontSize: 18, color: theme.mute, marginBottom: 18, ...fadeIn(frame, fps, 14) }}>
        PLAN  decompose → {spec.rules.length} atomic rules
      </div>

      {spec.rules.map((r, i) => (
        <Row key={r.n} rule={r} delay={rowStart + i * rowStagger} />
      ))}

      <div style={{ height: 1, background: theme.cardBorder, margin: "14px 0 16px", ...fadeIn(frame, fps, verdictDelay - 8) }} />

      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ fontFamily: theme.fontMono, fontSize: 20, color: theme.mute, ...fadeIn(frame, fps, verdictDelay - 6) }}>
          COVERAGE  {spec.coverage}
        </div>
        <div style={fadeUp(frame, fps, verdictDelay, 16)}>
          <Chip label={spec.verdict.label} color={statusColor[spec.verdict.status]} size="lg" />
        </div>
      </div>

      {spec.referral ? (
        <div style={{ fontFamily: theme.fontMono, fontSize: 22, color: theme.green, marginTop: 18, ...fadeUp(frame, fps, extraDelay, 16) }}>
          {spec.referral}
        </div>
      ) : null}
      {spec.missing ? (
        <div style={{ fontFamily: theme.fontMono, fontSize: 22, color: theme.amber, marginTop: 18, ...fadeUp(frame, fps, extraDelay, 16) }}>
          {spec.missing}
        </div>
      ) : null}
    </div>
  );
};
