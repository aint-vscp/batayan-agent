import React from "react";
import { AbsoluteFill } from "remotion";
import { theme } from "../theme";

export const Frame: React.FC = () => {
  return (
    <AbsoluteFill style={{ fontFamily: theme.fontSans }}>
      {/* wordmark, top-left */}
      <div style={{ position: "absolute", top: 46, left: 64, display: "flex", alignItems: "center", gap: 14 }}>
        <div style={{ width: 16, height: 16, borderRadius: 8, background: theme.violet }} />
        <div style={{ color: theme.ink, fontSize: 26, fontWeight: 800, letterSpacing: 1 }}>Batayan</div>
      </div>

      {/* bottom strip */}
      <div
        style={{
          position: "absolute",
          bottom: 40,
          left: 64,
          right: 64,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          color: theme.mute,
          fontSize: 22,
        }}
      >
        <div style={{ color: theme.azure, fontWeight: 700, letterSpacing: 1 }}>
          Microsoft Foundry · Foundry IQ
        </div>
        <div style={{ fontFamily: theme.fontMono }}>github.com/aint-vscp/batayan-agent</div>
      </div>
    </AbsoluteFill>
  );
};
