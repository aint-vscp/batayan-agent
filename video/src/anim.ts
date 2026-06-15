import { interpolate, spring } from "remotion";

export const fadeUp = (
  frame: number,
  fps: number,
  delay = 0,
  dist = 26,
  duration = 18
) => {
  const p = spring({
    frame: frame - delay,
    fps,
    config: { damping: 200 },
    durationInFrames: duration,
  });
  return {
    opacity: interpolate(p, [0, 1], [0, 1]),
    transform: `translateY(${interpolate(p, [0, 1], [dist, 0])}px)`,
  } as const;
};

export const fadeIn = (frame: number, fps: number, delay = 0, duration = 16) => {
  const p = spring({ frame: frame - delay, fps, config: { damping: 200 }, durationInFrames: duration });
  return { opacity: interpolate(p, [0, 1], [0, 1]) } as const;
};
