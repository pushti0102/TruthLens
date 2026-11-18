"""
TruthLens Test Image Generator for Live Demos
Creates an original PNG and a 1-pixel modified copy to demonstrate cryptographic tamper detection.
"""
import os
from PIL import Image, ImageDraw

def main():
    os.makedirs("demo_samples", exist_ok=True)
    orig_path = os.path.join("demo_samples", "original_demo.png")
    tampered_path = os.path.join("demo_samples", "tampered_demo.png")

    # 1. Create a 300x300 high contrast image
    img = Image.new("RGB", (300, 300), color=(15, 23, 42))
    draw = ImageDraw.Draw(img)
    draw.rectangle([50, 50, 250, 250], fill=(6, 182, 212), outline=(255, 255, 255), width=3)
    img.save(orig_path, format="PNG")
    print(f"[+] Created original sample: {orig_path}")

    # 2. Modify exactly 1 pixel
    pixels = img.load()
    r, g, b = pixels[100, 100]
    pixels[100, 100] = (r + 1, g, b)
    img.save(tampered_path, format="PNG")
    print(f"[+] Created tampered sample (1-pixel difference): {tampered_path}")
    print("[*] Ready for live registration and verification demo!")

if __name__ == "__main__":
    main()

