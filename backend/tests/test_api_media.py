import io
import random
import uuid
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from backend.app.main import app, startup_event

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_app():
    startup_event()


def create_unique_test_image(format="PNG", size=(64, 64)) -> bytes:
    r = random.randint(10, 240)
    g = random.randint(10, 240)
    b = random.randint(10, 240)
    img = Image.new("RGB", size, color=(r, g, b))
    # Write unique pixel at (0, 0) to ensure unique SHA-256
    img.putpixel((0, 0), (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))
    buf = io.BytesIO()
    img.save(buf, format=format)
    return buf.getvalue()


def get_publisher_token() -> str:
    res = client.post(
        "/api/auth/login",
        json={"email": "publisher@truthlens.local", "password": "PublisherPass123!"},
    )
    return res.json()["access_token"]


def test_media_registration_and_trusted_verification():
    token = get_publisher_token()
    img_bytes = create_unique_test_image()

    # 1. Register media as trusted publisher
    reg_res = client.post(
        "/api/publishers/register-media",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": (f"trusted_{uuid.uuid4().hex[:6]}.png", img_bytes, "image/png")},
        data={"issuer_id": "org_truthlens_official"},
    )
    assert reg_res.status_code == 201
    reg_data = reg_res.json()
    assert reg_data["schema_version"] == "1.0"
    assert "signature_b64" in reg_data
    assert len(reg_data["sha256"]) == 64
    registered_sha = reg_data["sha256"]

    # 2. Verify identical image
    verify_res = client.post(
        "/api/media/verify",
        files={"file": ("verify_copy.png", img_bytes, "image/png")},
    )
    assert verify_res.status_code == 200
    report = verify_res.json()
    assert report["sha256"] == registered_sha
    assert report["integrity"]["status"] == "MATCH"
    assert report["signature"]["status"] == "VALID"
    assert report["signature"]["key_trust_status"] == "TRUSTED"
    assert "VERIFIED" in report["trust_assessment"]["status"]
    assert report["trust_assessment"]["score"] >= 80


def test_integrity_mismatch_on_modified_image():
    token = get_publisher_token()
    # Create original image and register it
    img_orig = Image.new("RGB", (64, 64), color=(random.randint(50, 200), random.randint(50, 200), random.randint(50, 200)))
    img_orig.putpixel((1, 1), (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))
    buf_orig = io.BytesIO()
    img_orig.save(buf_orig, format="PNG")
    orig_bytes = buf_orig.getvalue()

    reg_res = client.post(
        "/api/publishers/register-media",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": (f"orig_{uuid.uuid4().hex[:6]}.png", orig_bytes, "image/png")},
    )
    assert reg_res.status_code == 201
    asset_id = reg_res.json()["asset_id"]

    # Modify 1 pixel
    img_modified = img_orig.copy()
    img_modified.putpixel((5, 5), (255, 0, 0))  # altered pixel
    buf_mod = io.BytesIO()
    img_modified.save(buf_mod, format="PNG")
    mod_bytes = buf_mod.getvalue()

    # Verify modified image referencing the asset_id
    verify_res = client.post(
        "/api/media/verify",
        files={"file": ("modified_image.png", mod_bytes, "image/png")},
        data={"asset_id": asset_id},
    )
    assert verify_res.status_code == 200
    report = verify_res.json()
    assert report["integrity"]["status"] == "MISMATCH"
    assert report["trust_assessment"]["status"] == "INTEGRITY_MISMATCH"
    assert report["trust_assessment"]["score"] <= 30


def test_unregistered_image_returns_inconclusive_without_error():
    # Fresh random unique image not registered in DB
    img_bytes = create_unique_test_image()

    verify_res = client.post(
        "/api/media/verify",
        files={"file": ("unregistered.png", img_bytes, "image/png")},
    )
    assert verify_res.status_code == 200
    report = verify_res.json()
    assert report["integrity"]["status"] == "NO_REFERENCE"
    assert report["signature"]["status"] == "MISSING"
    assert report["trust_assessment"]["status"] in ("INCONCLUSIVE", "SUSPICIOUS_AI")
    assert len(report["sha256"]) == 64


def test_unsupported_file_format_rejected_with_clean_400():
    fake_doc_bytes = b"This is a fictional DOCX document or text file masquerading as an image."

    res = client.post(
        "/api/media/verify",
        files={"file": ("fake_document.docx", fake_doc_bytes, "application/octet-stream")},
    )
    assert res.status_code == 400
    detail = res.json()["detail"]
    assert "error_code" in detail
    assert "message" in detail


def test_dashboard_summary():
    res = client.get("/api/dashboard/summary")
    assert res.status_code == 200
    data = res.json()
    assert data["total_verifications"] >= 1
    assert data["crypto_ready"] is True
    assert data["active_key_id"] is not None
