"""
scripts/test_model_routing_e2e.py
=================================
Verifies the complete model-routing and attribution pipeline:
1. Upload identical image with model=current
2. Upload same image with model=smaug
3. Verify different loaded model IDs and architectures
4. Verify invalid model returns explicit HTTP 400
5. Outputs raw JSON responses for inspection
"""

import sys
import json
from pathlib import Path
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

ai_root = PROJECT_ROOT / "truthlens-ai"
if str(ai_root) not in sys.path:
    sys.path.insert(0, str(ai_root))

from backend.app.main import app
from backend.app.database import SessionLocal
from backend.app.models.verification import VerificationRecord

def run_tests():
    client = TestClient(app)
    # Use reliably tracked sample photo
    test_img_path = PROJECT_ROOT / "demo_samples" / "real_dog_photo.jpg"
    if not test_img_path.exists():
        test_img_path = PROJECT_ROOT / "truthlens-ai" / "data" / "real" / "sample_photo.jpg"

    with open(test_img_path, "rb") as f:
        img_bytes = f.read()

    print(f"Testing with image: {test_img_path.name} ({len(img_bytes)} bytes)\n")

    # TEST 1: Upload with model=current
    print("--- TEST 1: Request with model='current' ---")
    res1 = client.post(
        "/api/media/verify",
        files={"file": (test_img_path.name, img_bytes, "image/jpeg")},
        data={"model": "current"},
    )
    print(f"Status Code: {res1.status_code}")
    data1 = res1.json()
    print("AI Response 1:")
    print(json.dumps(data1.get("ai"), indent=2))
    assert res1.status_code == 200, f"Expected 200, got {res1.status_code}"
    assert data1["ai"]["model_id"] == "dima806/ai_vs_real_image_detection"
    assert "vit" in data1["ai"]["architecture"].lower()

    # TEST 2: Upload with model=smaug
    print("\n--- TEST 2: Request with model='smaug' ---")
    res2 = client.post(
        "/api/media/verify",
        files={"file": (test_img_path.name, img_bytes, "image/jpeg")},
        data={"model": "smaug"},
    )
    print(f"Status Code: {res2.status_code}")
    data2 = res2.json()
    print("AI Response 2:")
    print(json.dumps(data2.get("ai"), indent=2))
    assert res2.status_code == 200, f"Expected 200, got {res2.status_code}"
    assert data2["ai"]["model_id"] == "abacusai/Smaug-AI-Image-Detector"
    assert "smaug" in data2["ai"]["architecture"].lower()

    # Verify separate models and architectures
    assert data1["ai"]["model_id"] != data2["ai"]["model_id"]
    assert data1["ai"]["architecture"] != data2["ai"]["architecture"]
    print("\nSUCCESS: Two separate model executions confirmed with distinct model IDs & architectures.")

    # TEST 3: Upload with invalid model
    print("\n--- TEST 3: Request with invalid model='invalid_custom_model' ---")
    res3 = client.post(
        "/api/media/verify",
        files={"file": (test_img_path.name, img_bytes, "image/jpeg")},
        data={"model": "invalid_custom_model"},
    )
    print(f"Status Code: {res3.status_code}")
    print(f"Response: {res3.json()}")
    assert res3.status_code == 400, f"Expected 400, got {res3.status_code}"
    assert res3.json()["detail"]["error_code"] == "INVALID_MODEL_SELECTION"
    print("SUCCESS: Explicit 400 Bad Request returned on invalid model; no silent fallback occurred.")

    # Output full JSON responses for reporting
    with open("data/test_model_routing_response_current.json", "w", encoding="utf-8") as f:
        json.dump(data1, f, indent=2)
    with open("data/test_model_routing_response_smaug.json", "w", encoding="utf-8") as f:
        json.dump(data2, f, indent=2)
    print("\nSaved full API responses to data/test_model_routing_response_current.json and data/test_model_routing_response_smaug.json")

if __name__ == "__main__":
    run_tests()
