import React from "react";
import { theme } from "../theme";

export const Chip: React.FC<{
  label: string;
  color: string;
  size?: "sm" | "lg";
  style?: React.CSSProperties;
}> = ({ label, color, size = "sm", style }) => {
  const lg = size === "lg";
  return (
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: lg ? 16 : 12,
        padding: lg ? "14px 26px" : "8px 16px",
        borderRadius: 999,
        border: `2px solid ${color}`,
        background: `${color}14`,
        color: theme.ink,
        fontFamily: theme.fontSans,
        fontWeight: 800,
        fontSize: lg ? 34 : 22,
        letterSpacing: 0.5,
        ...style,
      }}
    >
      <div
        style={{
          width: lg ? 18 : 13,
          height: lg ? 18 : 13,
          borderRadius: 999,
          background: color,
        }}
      />
      {label}
    </div>
  );
};
