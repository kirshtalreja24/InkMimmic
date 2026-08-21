# One shared interpreter for TensorFlow and PyTorch

Status: accepted

Segmentation and the character classifier are PyTorch; the diffusion generation model is TensorFlow. The research app and the generation glue need to call both in the same request.

We run both frameworks in one Python interpreter and one virtual environment (`requirements-app.txt`), rather than splitting them into separate processes or services.

**Consequences:** environment setup stays simple for a single-machine research/demo project — one venv, one process to launch — but the two frameworks' version constraints (e.g. TensorFlow>=2.16 for Python 3.12, numpy<2) have to be reconciled together in that one environment, and this choice would need to be revisited before either framework could scale independently (e.g. serving the generation model on a GPU box separate from the CPU-only segmentation/classifier path).
