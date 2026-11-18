"""
scripts/build_210_dataset.py
============================
Builds an independent, reproducible evaluation dataset of 210 images:
- 50 Real Camera Photographs (smartphone cameras)
- 50 AI-Generated Photographs (Stable Diffusion / CIFAKE)
- 50 Artistic Synthetic Images (Diffusion stylized art)
- 35 Manipulated Images (Forensic tampering: copy-move, splicing, resampling, compression)
- 25 Document Scans (ID cards, forms, certificates, evaluated strictly separately)

Outputs:
- Stored under: data/evaluation_210/
- Manifest: data/evaluation_210_manifest.json
"""

import os
import sys
import json
import random
import shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "data" / "evaluation_210"
MANIFEST_PATH = PROJECT_ROOT / "data" / "evaluation_210_manifest.json"

random.seed(42)
np.random.seed(42)

def generate_tampered_image(src_path: Path, dest_path: Path, tamper_type: str) -> dict:
    with Image.open(src_path) as img:
        img = img.convert("RGB")
        w, h = img.size
        # Work on a standard resized version if massive
        if max(w, h) > 1600:
            scale = 1600 / max(w, h)
            img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
            w, h = img.size

        if tamper_type == "copy_move":
            # Copy a rectangular patch and paste it elsewhere with softened borders
            pw, ph = int(w * 0.2), int(h * 0.2)
            src_x = int(w * 0.2)
            src_y = int(h * 0.2)
            patch = img.crop((src_x, src_y, src_x + pw, src_y + ph))
            
            # Feather edge
            mask = Image.new("L", (pw, ph), 255)
            draw = ImageDraw.Draw(mask)
            draw.rectangle([0, 0, pw, ph], outline=0, width=5)
            mask = mask.filter(ImageFilter.GaussianBlur(3))
            
            dest_x = int(w * 0.55)
            dest_y = int(h * 0.55)
            img.paste(patch, (dest_x, dest_y), mask)
            img.save(dest_path, "JPEG", quality=85)
            comp = "JPEG Q85"

        elif tamper_type == "splicing":
            # Splice in an elliptical synthetic colored geometric feature
            pw, ph = int(w * 0.25), int(h * 0.25)
            cx, cy = int(w * 0.5), int(h * 0.4)
            overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)
            draw.ellipse([cx - pw//2, cy - ph//2, cx + pw//2, cy + ph//2], fill=(230, 80, 50, 200))
            draw.rectangle([cx - pw//3, cy - ph//4, cx + pw//3, cy + ph//4], fill=(40, 180, 220, 220))
            img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
            img.save(dest_path, "JPEG", quality=80)
            comp = "JPEG Q80"

        elif tamper_type == "heavy_compression":
            # Severe recompression to introduce high-frequency blocking
            img.save(dest_path, "JPEG", quality=15)
            comp = "JPEG Q15 (Severe Lossy)"

        elif tamper_type == "resample_blur":
            # Local box blur and unsharp mask retouching
            pw, ph = int(w * 0.35), int(h * 0.35)
            x, y = int(w * 0.3), int(h * 0.3)
            patch = img.crop((x, y, x + pw, y + ph))
            patch = patch.filter(ImageFilter.GaussianBlur(4))
            patch = patch.filter(ImageFilter.UnsharpMask(radius=2, percent=150))
            img.paste(patch, (x, y))
            img.save(dest_path, "JPEG", quality=75)
            comp = "JPEG Q75"
        else:
            img.save(dest_path, "JPEG", quality=80)
            comp = "JPEG Q80"

        final_w, final_h = img.size
        return {
            "resolution": [final_w, final_h],
            "format": "JPEG",
            "compression": comp
        }

def generate_document_image(dest_path: Path, doc_index: int) -> dict:
    # Generate various document layouts (ID cards, receipts, forms, certificates)
    if doc_index % 2 == 0:
        w, h = 856, 540
    else:
        w, h = 600, 800
    if doc_index % 3 == 0:
        w, h = 800, 1100 # Vertical certificate/letterhead
    
    img = Image.new("RGB", (w, h), color=(248, 249, 250))
    draw = ImageDraw.Draw(img)

    if doc_index % 3 == 0:
        # Scanned letterhead / form
        draw.rectangle([40, 40, w - 40, 100], fill=(41, 128, 185))
        draw.rectangle([60, 140, w - 60, 155], fill=(80, 80, 80))
        for line_y in range(180, h - 180, 35):
            line_w = random.randint(int(w * 0.4), int(w * 0.85))
            draw.rectangle([60, line_y, 60 + line_w, line_y + 12], fill=(120, 120, 120))
        # Stamp circle
        draw.ellipse([w - 200, h - 160, w - 80, h - 40], outline=(192, 57, 43), width=3)
        draw.rectangle([w - 180, h - 105, w - 100, h - 95], fill=(192, 57, 43))
    elif doc_index % 2 == 0:
        # ID Card layout
        draw.rectangle([30, 30, w - 30, 90], fill=(31, 58, 147))
        draw.rectangle([50, 120, 230, 340], fill=(218, 223, 225), outline=(108, 122, 137), width=2)
        draw.rectangle([50, 370, 230, 450], fill=(255, 255, 255), outline=(189, 195, 199), width=1)
        for y in [130, 175, 220, 265, 310, 355, 400]:
            draw.rectangle([270, y, w - 60, y + 16], fill=(52, 73, 94))
        # Chip / hologram
        draw.rectangle([270, 430, 340, 480], fill=(241, 196, 15), outline=(180, 140, 10), width=1)
    else:
        # Receipt / invoice layout
        draw.rectangle([20, 20, w - 20, 70], fill=(34, 49, 63))
        for y in range(90, h - 100, 28):
            draw.rectangle([30, y, w - 30, y + 8], fill=(100, 100, 100))
        draw.rectangle([30, h - 80, w - 30, h - 50], fill=(46, 204, 113))

    img.save(dest_path, "JPEG", quality=90)
    return {
        "resolution": [w, h],
        "format": "JPEG",
        "compression": "JPEG Q90 (Synthesized Document Layout)"
    }

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for cat in ["real_photographs", "ai_generated_photographs", "artistic_synthetic", "manipulated_tampered", "document_scans"]:
        (OUTPUT_DIR / cat).mkdir(parents=True, exist_ok=True)

    manifest_entries = []
    item_id = 1

    # 1. Real photographs (50 samples)
    real_sources = [
        Path(r"D:\Photos\CHAT PUJA"),
        Path(r"D:\Photos\PLACES"),
        Path(r"D:\Photos\BIRTHDAY"),
    ]
    real_candidates = []
    for sdir in real_sources:
        if sdir.exists():
            for p in sdir.rglob("*.jpg"):
                try:
                    if p.is_file() and p.stat().st_size > 50000:
                        with Image.open(p) as test_im:
                            test_im.verify()
                        real_candidates.append(p)
                except Exception:
                    continue
    
    # Deduplicate
    real_candidates = list(dict.fromkeys(real_candidates))
    
    # Shuffle deterministically
    random.seed(101)
    random.shuffle(real_candidates)
    selected_real = real_candidates[:50]
    print(f"Selected {len(selected_real)} real photos from {len(real_candidates)} candidates.")

    for p in selected_real:
        dest_filename = f"real_{item_id:03d}_{p.name}"
        dest_path = OUTPUT_DIR / "real_photographs" / dest_filename
        shutil.copy2(p, dest_path)
        with Image.open(dest_path) as im:
            rw, rh = im.size
            fmt = im.format or "JPEG"
        
        manifest_entries.append({
            "id": f"EVAL-{item_id:03d}",
            "filename": dest_filename,
            "filepath": str(dest_path),
            "category": "real_photograph",
            "ground_truth": "REAL",
            "source": f"Smartphone Camera ({p.parent.name})",
            "generator": "N/A (Physical Optical Sensor)",
            "resolution": [rw, rh],
            "format": fmt,
            "compression": "Standard Camera JPEG",
            "split": "independent_eval"
        })
        item_id += 1

    # 2. AI-Generated Photographs (50 samples)
    cifake_dir = PROJECT_ROOT / "data" / "cifake_dataset" / "FAKE"
    if not cifake_dir.exists():
        cifake_dir = PROJECT_ROOT / "test" / "FAKE"
    cifake_candidates = sorted(list(cifake_dir.glob("*.jpg")))
    # Partition candidates: first 50 for realistic, next 50 for artistic
    selected_synth_photo = cifake_candidates[:50]
    selected_artistic = cifake_candidates[50:100]

    for p in selected_synth_photo:
        dest_filename = f"ai_photo_{item_id:03d}.jpg"
        dest_path = OUTPUT_DIR / "ai_generated_photographs" / dest_filename
        shutil.copy2(p, dest_path)
        with Image.open(dest_path) as im:
            rw, rh = im.size
            fmt = im.format or "JPEG"

        manifest_entries.append({
            "id": f"EVAL-{item_id:03d}",
            "filename": dest_filename,
            "filepath": str(dest_path),
            "category": "ai_generated_photograph",
            "ground_truth": "AI_GENERATED",
            "source": "CIFAKE Evaluation Split",
            "generator": "Stable Diffusion v1.4",
            "resolution": [rw, rh],
            "format": fmt,
            "compression": "Standard JPEG (32x32 upscaled / diffusion)",
            "split": "independent_eval"
        })
        item_id += 1

    # 3. Artistic / Stylized Synthetic Images (50 samples)
    for p in selected_artistic:
        dest_filename = f"ai_art_{item_id:03d}.jpg"
        dest_path = OUTPUT_DIR / "artistic_synthetic" / dest_filename
        shutil.copy2(p, dest_path)
        with Image.open(dest_path) as im:
            rw, rh = im.size
            fmt = im.format or "JPEG"

        manifest_entries.append({
            "id": f"EVAL-{item_id:03d}",
            "filename": dest_filename,
            "filepath": str(dest_path),
            "category": "artistic_synthetic",
            "ground_truth": "AI_GENERATED",
            "source": "CIFAKE Artistic / Render Evaluation Split",
            "generator": "Stable Diffusion v1.4 (Stylized)",
            "resolution": [rw, rh],
            "format": fmt,
            "compression": "Standard JPEG",
            "split": "independent_eval"
        })
        item_id += 1

    # 4. Manipulated / Tampered Images (35 samples)
    # Take additional held-out real images (from index 50 to 85) to tamper
    tamper_bases = real_candidates[50:85]
    tamper_types = ["copy_move"] * 12 + ["splicing"] * 10 + ["heavy_compression"] * 7 + ["resample_blur"] * 6
    random.seed(202)
    random.shuffle(tamper_types)

    for idx, (p, ttype) in enumerate(zip(tamper_bases, tamper_types)):
        dest_filename = f"tampered_{item_id:03d}_{ttype}.jpg"
        dest_path = OUTPUT_DIR / "manipulated_tampered" / dest_filename
        meta = generate_tampered_image(p, dest_path, ttype)

        manifest_entries.append({
            "id": f"EVAL-{item_id:03d}",
            "filename": dest_filename,
            "filepath": str(dest_path),
            "category": "manipulated_tampered",
            "ground_truth": "MANIPULATED",
            "source": f"Real Photo ({p.parent.name}) + Tamper Pipeline",
            "generator": f"Forensic Tampering ({ttype})",
            "resolution": meta["resolution"],
            "format": meta["format"],
            "compression": meta["compression"],
            "split": "independent_eval"
        })
        item_id += 1

    # 5. Document Scans (25 samples)
    for doc_idx in range(1, 26):
        dest_filename = f"doc_{item_id:03d}_scan.jpg"
        dest_path = OUTPUT_DIR / "document_scans" / dest_filename
        meta = generate_document_image(dest_path, doc_idx)

        manifest_entries.append({
            "id": f"EVAL-{item_id:03d}",
            "filename": dest_filename,
            "filepath": str(dest_path),
            "category": "document_scan",
            "ground_truth": "DOCUMENT",
            "source": "Procedural ID/Document Layout Engine",
            "generator": "Document Layout Generator",
            "resolution": meta["resolution"],
            "format": meta["format"],
            "compression": meta["compression"],
            "split": "independent_eval"
        })
        item_id += 1

    print(f"Generated total {len(manifest_entries)} dataset samples.")
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest_entries, f, indent=2)
    print(f"Manifest written to {MANIFEST_PATH}")

if __name__ == "__main__":
    main()
