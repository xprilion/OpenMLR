"""Compute background tasks — health checks and periodic maintenance."""

import asyncio
import logging
from datetime import UTC, datetime

from ..celery_app import celery_app
from ..compute import WorkspaceManager
from ..db import operations as ops
from ..db.engine import get_worker_session

logger = logging.getLogger(__name__)


@celery_app.task
def cleanup_old_workspaces():
    """Clean up old workspace archives and orphaned workspaces."""
    wm = WorkspaceManager()

    # Clean old archives
    archive_result = wm.cleanup_archives(max_age_days=30, max_count=100)
    logger.info(
        f"Archive cleanup: deleted {archive_result['deleted']} archives, "
        f"freed {archive_result['freed_bytes'] / (1024**3):.1f} GB"
    )

    # Clean orphaned workspaces (conversations that no longer exist)
    async def _cleanup_orphaned():
        session_factory = get_worker_session()
        async with session_factory() as db:
            from sqlalchemy import select

            from ..db.models import Conversation

            result = await db.execute(select(Conversation.uuid))
            active_uuids = {row[0] for row in result.all()}

            ws_result = wm.cleanup_workspaces(
                conversation_uuids=list(active_uuids),
                archive=True,
            )
            logger.info(
                f"Workspace cleanup: deleted {ws_result['deleted']} workspaces, "
                f"freed {ws_result['freed_bytes'] / (1024**3):.1f} GB"
            )

    asyncio.run(_cleanup_orphaned())


@celery_app.task(bind=True, max_retries=3)
def check_compute_node_health(self, node_id: int, user_id: int):
    """Check health of a single compute node."""

    async def _check():
        session_factory = get_worker_session()
        async with session_factory() as db:
            node = await ops.get_compute_node_by_id(db, node_id, user_id)
            if not node:
                logger.warning(f"Node {node_id} not found for health check")
                return

            from ..compute.probe import probe_sandbox
            from ..sandbox.manager import SandboxManager

            sm = SandboxManager(workspace_manager=WorkspaceManager())
            try:
                await sm.create(node.type, node.config)
                sandbox = sm.get_active()

                if sandbox:
                    caps = await probe_sandbox(sandbox)
                    await ops.update_compute_node(
                        db,
                        node.id,
                        user_id,
                        capabilities=caps.to_dict(),
                        health_status="online",
                        last_seen_at=datetime.now(UTC),
                    )
                    logger.info(f"Health check passed for node '{node.name}'")
                else:
                    await ops.update_compute_node(
                        db,
                        node.id,
                        user_id,
                        health_status="offline",
                    )
                    logger.warning(
                        f"Health check failed for node '{node.name}': sandbox not created"
                    )
            except Exception as e:
                await ops.update_compute_node(
                    db,
                    node.id,
                    user_id,
                    health_status="offline",
                )
                logger.warning(f"Health check failed for node '{node.name}': {e}")
            finally:
                await sm.destroy()

    asyncio.run(_check())


@celery_app.task
def health_check_all_nodes():
    """Run health checks on all compute nodes for all users."""

    async def _check_all():
        session_factory = get_worker_session()
        async with session_factory() as db:
            from sqlalchemy import select

            from ..db.models import User

            result = await db.execute(select(User))
            users = result.scalars().all()

            for user in users:
                nodes = await ops.get_compute_nodes(db, user.id)
                for node in nodes:
                    check_compute_node_health.delay(node.id, user.id)

    asyncio.run(_check_all())
    logger.info("Queued health checks for all compute nodes")
