import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { theme } from "../theme";
import { fadeUp } from "../anim";

export const Caption: React.FC<{ text: string }> = ({ text }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const style = fadeUp(frame, fps, 4, 18);
  return (
    <div
      style={{
        position: "absolute",
        bottom: 120,
        left: 0,
        right: 0,
        display: "flex",
        justifyContent: "center",
        ...style,
      }}
    >
      <div
        style={{
          fontFamily: theme.fontSans,
          fontSize: 32,
          fontWeight: 600,
          color: theme.ink,
          background: "rgba(8,6,16,0.55)",
          border: `1px solid ${theme.cardBorder}`,
          borderRadius: 14,
          padding: "14px 26px",
          maxWidth: 1300,
          textAlign: "center",
          backdropFilter: "blur(2px)",
        }}
      >
        {text}
      </div>
    </div>
  );
};
