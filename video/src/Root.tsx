import React from "react";
import { Composition } from "remotion";
import { Demo } from "./Demo";
import { totalFrames, fps } from "./timeline";

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="BatayanDemo"
      component={Demo}
      durationInFrames={Math.max(1, totalFrames)}
      fps={fps}
      width={1920}
      height={1080}
    />
  );
};
