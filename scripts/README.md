# TruthLens Automation & Benchmarking Scripts

This directory contains standalone automation scripts for benchmarking, dataset generation, and verification testing.

---

## Scripts Inventory

| Script | Purpose | Usage |
|--------|---------|-------|
| `build_210_dataset.py` | Assembles the 210-image independent evaluation dataset and builds the metadata manifest. | `python scripts/build_210_dataset.py` |
| `run_210_benchmark.py` | Executes the comprehensive 210-image benchmark comparing Standard ViT vs. Smaug detectors with full confusion matrices. | `python scripts/run_210_benchmark.py` |
| `benchmark_models.py` | Comparative inference test runner across loaded pretrained models. | `python scripts/benchmark_models.py` |
| `test_model_routing_e2e.py` | End-to-end integration test validating multi-model selection (`current` vs `smaug`), model disagreement detection, and invalid model rejection (`400 Bad Request`). | `python scripts/test_model_routing_e2e.py` |
| `generate_test_images.py` | Generates identical original and 1-pixel tampered images for demonstration of SHA-256 bitwise integrity verification. | `python scripts/generate_test_images.py` |
| `test_verify_pipeline.py` | Submits a multipart media verification request to the running local FastAPI backend. | `python scripts/test_verify_pipeline.py` |
