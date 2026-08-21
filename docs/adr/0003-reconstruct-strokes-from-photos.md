# Reconstruct strokes from photos instead of capturing them live

Status: accepted

The diffusion model needs online stroke data — `(dx, dy, pen_up)` sequences with real pen order and timing — to fine-tune on, but this project only has offline page photos. Building a stylus/tablet capture tool to collect real online data was the higher-fidelity option but estimated at roughly a day of extra tooling work.

We instead reconstruct approximate online strokes from the existing offline photos (skeletonize → trace → resample), rather than building a live capture tool (Option A) or skipping fine-tuning entirely and relying only on inference-time style transfer (Option C, the zero-effort fallback).

**Consequences:** fine-tuning is possible without new data collection, but pen order, timing, and loop/crossing resolution are inferred, not real. Reconstructed strokes are an honest approximation — this is documented as a fidelity ceiling everywhere the project discusses limitations, and it's the reason generation output will never be indistinguishable from a writer's real hand.
