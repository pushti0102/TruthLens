# TruthLens Demo Samples

Curated sample media assets for live demonstrations and testing of TruthLens verification features.

---

## Sample Media Assets

| File | Type | Expected TruthLens Assessment |
|------|------|--------------------------------|
| `original_demo.png` | Authoritative Media | Clean PNG image designed to be registered via the Publisher Portal with ECDSA signature. |
| `tampered_demo.png` | Bitwise Tampered | Copy of `original_demo.png` with a single modified pixel; triggers `INTEGRITY_MISMATCH` (*Tamper Detected*). |
| `real_dog_photo.jpg` | Smartphone Photograph | Natural camera photograph evaluated for real-world artifact analysis. |
| `ai_generated_anime.png` | Synthetic Graphic | AI-generated diffusion artwork designed to test visual artifact detection. |
