import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { theme } from "../theme";
import { fadeUp } from "../anim";

export const Outro: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", fontFamily: theme.fontSans }}>
      <div style={{ textAlign: "center", marginTop: -30 }}>
        <div style={{ color: theme.ink, fontSize: 64, fontWeight: 800, maxWidth: 1300, lineHeight: 1.25, ...fadeUp(frame, fps, 2) }}>
          It shows its work,
          <br />
          and never bluffs.
        </div>
        <div style={{ color: theme.azure, fontSize: 40, fontWeight: 800, marginTop: 36, ...fadeUp(frame, fps, 16) }}>
          Batayan — because every answer deserves a basis.
        </div>
        <div
          style={{
            display: "inline-block",
            marginTop: 40,
            fontFamily: theme.fontMono,
            fontSize: 28,
            color: theme.ink,
            border: `1px solid ${theme.cardBorder}`,
            borderRadius: 12,
            padding: "12px 24px",
            background: "rgba(8,6,16,0.5)",
            ...fadeUp(frame, fps, 26),
          }}
        >
          github.com/aint-vscp/batayan-agent
        </div>
      </div>
    </AbsoluteFill>
  );
};
