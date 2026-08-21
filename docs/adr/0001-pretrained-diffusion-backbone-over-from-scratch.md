# Pretrained stroke-diffusion backbone instead of training a generator from scratch

Status: accepted

This project's own handwriting samples amount to roughly 70–200 character crops per writer — far short of what a generative model needs to train from scratch. We build on `tcl9876/Diffusion-Handwriting-Generation`, a stroke-level diffusion model pretrained on the IAM handwriting database (arXiv:2011.06704), rather than training a character-level GAN from scratch (the original plan) or from-scratch diffusion.

**Considered options:** a character-level conditional GAN trained from scratch was ruled out — nowhere near enough per-class samples to converge. HiGAN+ (another pretrained option) was also considered and rejected in favor of this backbone: it generates full strings in one pass instead of word-at-a-time, has a simpler five-file codebase, and carries a permissive license. Full reasoning in `plan.md`.

**Consequences:** generation is stroke-level (online pen data), not pixel-level — the project needed a way to get stroke data out of its offline photo captures (see ADR 0003) — and it inherits the base model's fixed 73-token ASCII vocabulary and ~480-point / 50-token sequence-length limits.
