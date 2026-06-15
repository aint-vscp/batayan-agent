import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { theme } from "../theme";
import { fadeUp } from "../anim";
import { Chip } from "./Chip";

export const Intro: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", fontFamily: theme.fontSans }}>
      <div style={{ textAlign: "center", marginTop: -40 }}>
        <div style={{ color: theme.azure, fontSize: 24, fontWeight: 800, letterSpacing: 5, ...fadeUp(frame, fps, 2) }}>
          MICROSOFT AGENTS LEAGUE · REASONING AGENTS
        </div>
        <div style={{ color: theme.ink, fontSize: 150, fontWeight: 900, marginTop: 10, ...fadeUp(frame, fps, 8) }}>
          Batayan
        </div>
        <div style={{ color: theme.azure, fontSize: 44, fontWeight: 800, ...fadeUp(frame, fps, 16) }}>
          AI that argues with receipts
        </div>
        <div style={{ color: theme.mute, fontSize: 24, marginTop: 12, ...fadeUp(frame, fps, 22) }}>
          Filipino: basis · grounds · foundation
        </div>
        <div style={{ display: "flex", gap: 18, justifyContent: "center", marginTop: 40, ...fadeUp(frame, fps, 30) }}>
          <Chip label="ELIGIBLE" color={theme.green} />
          <Chip label="INELIGIBLE" color={theme.red} />
          <Chip label="INSUFFICIENT EVIDENCE" color={theme.amber} />
        </div>
      </div>
    </AbsoluteFill>
  );
};
