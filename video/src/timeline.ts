import timelineJson from "../public/audio/timeline.json";

export type Segment = {
  id: string;
  text: string;
  file: string;
  duration: number;
  frames: number;
  caption: string;
};

export const timeline = timelineJson as unknown as {
  fps: number;
  voice: string;
  engine: string;
  segments: Segment[];
  total_seconds: number;
};

// Tail frames added to each scene so the narration audio fully plays out and the
// scene gets a short breath before the next one.
export const PAD = 18;

export const segments = timeline.segments;
export const fps = timeline.fps;
export const totalFrames = segments.reduce((a, s) => a + s.frames + PAD, 0);
