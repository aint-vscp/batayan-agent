import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { theme } from "../theme";
import { fadeUp } from "../anim";
import { Ledger } from "./Ledger";
import type { SceneSpec } from "../scenes";

export const Beat: React.FC<{ spec: Extract<SceneSpec, { kind: "beat" }> }> = ({ spec }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", fontFamily: theme.fontSans }}>
      <div style={{ marginTop: -56, marginBottom: 22, textAlign: "center", ...fadeUp(frame, fps, 0, 18) }}>
        <span style={{ color: theme.ink, fontSize: 30, fontWeight: 800 }}>{spec.subject}</span>
        <span style={{ color: theme.mute, fontSize: 30 }}>{"  ·  "}</span>
        <span style={{ color: theme.gray, fontSize: 30 }}>{spec.program}</span>
      </div>
      <Ledger spec={spec} />
    </AbsoluteFill>
  );
};
