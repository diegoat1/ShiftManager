import pytest

from app.models.document import Document
from app.utils.enums import VerificationStatus


@pytest.mark.asyncio
async def test_list_document_types(client, seed_document_types):
    resp = await client.get("/api/v1/document-types/")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3


@pytest.mark.asyncio
async def test_doctor_no_documents(client, medico_headers, sample_doctor_with_user):
    resp = await client.get("/api/v1/me/documents/", headers=medico_headers)
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_admin_list_documents(client, admin_headers):
    resp = await client.get("/api/v1/admin/documents/", headers=admin_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_admin_approve_document(client, admin_headers, session, sample_doctor_with_user, seed_document_types):
    doc = Document(
        doctor_id=sample_doctor_with_user.id,
        document_type_id=seed_document_types["assicurazione"].id,
        file_path="/uploads/test.pdf",
        original_filename="test.pdf",
        file_size_bytes=1000,
        mime_type="application/pdf",
    )
    session.add(doc)
    await session.flush()

    resp = await client.post(f"/api/v1/admin/documents/{doc.id}/approve", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["verification_status"] == "approved"


@pytest.mark.asyncio
async def test_admin_reject_document(client, admin_headers, session, sample_doctor_with_user, seed_document_types):
    doc = Document(
        doctor_id=sample_doctor_with_user.id,
        document_type_id=seed_document_types["cv"].id,
        file_path="/uploads/cv.pdf",
        original_filename="cv.pdf",
        file_size_bytes=2000,
        mime_type="application/pdf",
    )
    session.add(doc)
    await session.flush()

    resp = await client.post(f"/api/v1/admin/documents/{doc.id}/reject", headers=admin_headers, json={
        "status": "rejected",
        "rejection_reason": "Documento illeggibile",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["verification_status"] == "rejected"
    assert data["rejection_reason"] == "Documento illeggibile"
