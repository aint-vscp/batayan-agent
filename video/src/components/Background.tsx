import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { theme } from "../theme";

export const Background: React.FC = () => {
  const frame = useCurrentFrame();
  // very slow drift on the glow so static frames feel alive
  const gx = 22 + Math.sin(frame / 90) * 4;
  const gy = 18 + Math.cos(frame / 110) * 3;
  return (
    <AbsoluteFill style={{ backgroundColor: theme.bg1 }}>
      <AbsoluteFill
        style={{
          background: `radial-gradient(120% 90% at ${gx}% ${gy}%, #1b1340 0%, ${theme.bg0} 45%, ${theme.bg1} 100%)`,
        }}
      />
      <AbsoluteFill
        style={{
          background: `radial-gradient(40% 40% at 85% 12%, rgba(56,189,248,0.10), transparent 70%)`,
        }}
      />
    </AbsoluteFill>
  );
};
