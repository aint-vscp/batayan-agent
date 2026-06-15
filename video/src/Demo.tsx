import React from "react";
import { AbsoluteFill, Audio, Sequence, staticFile } from "remotion";
import { segments, PAD } from "./timeline";
import { scenes } from "./scenes";
import { Background } from "./components/Background";
import { Frame } from "./components/Frame";
import { Caption } from "./components/Caption";
import { Intro } from "./components/Intro";
import { Outro } from "./components/Outro";
import { Beat } from "./components/Beat";

const Scene: React.FC<{ id: string }> = ({ id }) => {
  const spec = scenes[id];
  if (!spec) return null;
  if (spec.kind === "intro") return <Intro />;
  if (spec.kind === "outro") return <Outro />;
  return <Beat spec={spec} />;
};

export const Demo: React.FC = () => {
  let cursor = 0;
  const placed = segments.map((seg) => {
    const from = cursor;
    const durationInFrames = seg.frames + PAD;
    cursor += durationInFrames;
    return { seg, from, durationInFrames };
  });

  return (
    <AbsoluteFill style={{ backgroundColor: "#080610" }}>
      <Background />
      {placed.map(({ seg, from, durationInFrames }) => (
        <Sequence key={seg.id} from={from} durationInFrames={durationInFrames} name={seg.id}>
          <Scene id={seg.id} />
          <Audio src={staticFile(seg.file)} />
          <Caption text={seg.caption} />
        </Sequence>
      ))}
      <Frame />
    </AbsoluteFill>
  );
};
