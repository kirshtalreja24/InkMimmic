# Fine-tune the decoder only; keep the style extractor frozen

Status: accepted

Per-writer fine-tuning runs on a handful of reconstructed lines per writer — nowhere near enough data to retrain a full model without wrecking what IAM pretraining already captured. Fine-tuning therefore only ever touches the diffusion decoder's weights; the style extractor (a MobileNetV2 image encoder) stays frozen at its pretrained weights for both inference and every per-writer fine-tune.

**Consequences:** style vectors can be precomputed once per style reference and reused across a whole page, and catastrophic forgetting on tiny per-writer datasets is avoided. The cost is a style-fidelity ceiling: generation can only ever condition on what the frozen extractor's feature space already represents — it will never learn new visual style features from a writer's samples, only reweight the ones IAM pretraining already gave it.
