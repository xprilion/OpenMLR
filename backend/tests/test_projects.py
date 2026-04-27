"""Tests for Project model, DB operations, and API routes."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from openmlr.db import operations as ops
from openmlr.db.models import User

pytestmark = pytest.mark.asyncio


# ── DB Operations ────────────────────────────────────────


class TestProjectOperations:
    async def test_create_project(self, db_session: AsyncSession, test_user: User):
        project = await ops.create_project(
            db_session,
            test_user.id,
            name="Test Project",
            slug="test-project",
            description="A test project",
        )
        assert project.id is not None
        assert project.uuid is not None
        assert project.name == "Test Project"
        assert project.slug == "test-project"
        assert project.status == "active"

    async def test_get_user_projects(self, db_session: AsyncSession, test_user: User):
        await ops.create_project(db_session, test_user.id, "P1", "p1")
        await ops.create_project(db_session, test_user.id, "P2", "p2")

        projects = await ops.get_user_projects(db_session, test_user.id)
        assert len(projects) == 2

    async def test_get_project_by_uuid(self, db_session: AsyncSession, test_user: User):
        project = await ops.create_project(db_session, test_user.id, "Find Me", "find-me")
        found = await ops.get_project_by_uuid(db_session, project.uuid, test_user.id)
        assert found is not None
        assert found.name == "Find Me"

    async def test_get_project_by_uuid_wrong_user(self, db_session: AsyncSession, test_user: User):
        project = await ops.create_project(db_session, test_user.id, "Private", "private")
        found = await ops.get_project_by_uuid(db_session, project.uuid, user_id=9999)
        assert found is None

    async def test_get_project_by_slug(self, db_session: AsyncSession, test_user: User):
        await ops.create_project(db_session, test_user.id, "Slug Test", "slug-test")
        found = await ops.get_project_by_slug(db_session, test_user.id, "slug-test")
        assert found is not None
        assert found.name == "Slug Test"

    async def test_update_project(self, db_session: AsyncSession, test_user: User):
        project = await ops.create_project(db_session, test_user.id, "Original", "original")
        updated = await ops.update_project(
            db_session,
            project.id,
            test_user.id,
            name="Updated Name",
            description="New description",
        )
        assert updated.name == "Updated Name"
        assert updated.description == "New description"

    async def test_archive_project(self, db_session: AsyncSession, test_user: User):
        project = await ops.create_project(db_session, test_user.id, "To Archive", "to-archive")
        archived = await ops.archive_project(db_session, project.id, test_user.id)
        assert archived.status == "archived"

    async def test_get_user_projects_excludes_archived(
        self, db_session: AsyncSession, test_user: User
    ):
        await ops.create_project(db_session, test_user.id, "Active", "active")
        p2 = await ops.create_project(db_session, test_user.id, "To Archive", "to-archive")
        await ops.archive_project(db_session, p2.id, test_user.id)

        active_only = await ops.get_user_projects(db_session, test_user.id, include_archived=False)
        assert len(active_only) == 1
        assert active_only[0].name == "Active"

        all_projects = await ops.get_user_projects(db_session, test_user.id, include_archived=True)
        assert len(all_projects) == 2

    async def test_attach_conversation_to_project(self, db_session: AsyncSession, test_user: User):
        project = await ops.create_project(db_session, test_user.id, "With Conv", "with-conv")
        conv = await ops.create_conversation(db_session, test_user.id, title="Test Conv")

        success = await ops.attach_conversation_to_project(db_session, conv.id, project.id)
        assert success is True

        convs = await ops.get_project_conversations(db_session, project.id)
        assert len(convs) == 1
        assert convs[0].title == "Test Conv"

    async def test_detach_conversation_from_project(
        self, db_session: AsyncSession, test_user: User
    ):
        project = await ops.create_project(db_session, test_user.id, "Detach Test", "detach-test")
        conv = await ops.create_conversation(db_session, test_user.id, project_id=project.id)

        convs = await ops.get_project_conversations(db_session, project.id)
        assert len(convs) == 1

        await ops.attach_conversation_to_project(db_session, conv.id, None)
        convs = await ops.get_project_conversations(db_session, project.id)
        assert len(convs) == 0

    async def test_create_conversation_with_project(
        self, db_session: AsyncSession, test_user: User
    ):
        project = await ops.create_project(db_session, test_user.id, "Direct", "direct")
        conv = await ops.create_conversation(
            db_session,
            test_user.id,
            title="Project Conv",
            project_id=project.id,
        )
        assert conv.project_id == project.id


# ── API Routes ───────────────────────────────────────────


class TestProjectRoutes:
    async def test_create_project_api(self, auth_client):
        resp = await auth_client.post(
            "/api/projects",
            json={
                "name": "API Project",
                "description": "Created via API",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["project"]["name"] == "API Project"
        assert data["project"]["slug"] == "api-project"
        assert data["project"]["status"] == "active"

    async def test_list_projects_api(self, auth_client):
        await auth_client.post("/api/projects", json={"name": "Project 1"})
        await auth_client.post("/api/projects", json={"name": "Project 2"})

        resp = await auth_client.get("/api/projects")
        assert resp.status_code == 200
        data = resp.json()
        # The endpoint auto-creates a default project, so filter it out
        non_default = [p for p in data["projects"] if not p.get("is_default")]
        assert len(non_default) == 2

    async def test_get_project_api(self, auth_client):
        create_resp = await auth_client.post("/api/projects", json={"name": "Get Me"})
        uuid = create_resp.json()["project"]["uuid"]

        resp = await auth_client.get(f"/api/projects/{uuid}")
        assert resp.status_code == 200
        assert resp.json()["project"]["name"] == "Get Me"

    async def test_update_project_api(self, auth_client):
        create_resp = await auth_client.post("/api/projects", json={"name": "Update Me"})
        uuid = create_resp.json()["project"]["uuid"]

        resp = await auth_client.put(
            f"/api/projects/{uuid}",
            json={
                "name": "Updated",
                "description": "New desc",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["project"]["name"] == "Updated"

    async def test_delete_project_api(self, auth_client):
        create_resp = await auth_client.post("/api/projects", json={"name": "Delete Me"})
        uuid = create_resp.json()["project"]["uuid"]

        resp = await auth_client.delete(f"/api/projects/{uuid}")
        assert resp.status_code == 200

        # Should be archived, not truly deleted
        get_resp = await auth_client.get(f"/api/projects/{uuid}")
        assert get_resp.json()["project"]["status"] == "archived"

    async def test_create_project_missing_name(self, auth_client):
        resp = await auth_client.post("/api/projects", json={})
        assert resp.status_code == 400

    async def test_get_nonexistent_project(self, auth_client):
        resp = await auth_client.get("/api/projects/nonexistent-uuid")
        assert resp.status_code == 404

    async def test_project_conversations_api(self, auth_client):
        create_resp = await auth_client.post("/api/projects", json={"name": "Conv Test"})
        uuid = create_resp.json()["project"]["uuid"]

        resp = await auth_client.get(f"/api/projects/{uuid}/conversations")
        assert resp.status_code == 200
        assert resp.json()["conversations"] == []
