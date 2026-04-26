"""Tests for Celery app configuration."""

import pytest
from celery import Celery


class TestCeleryApp:
    def test_is_celery_instance(self):
        from openmlr.celery_app import celery_app
        assert isinstance(celery_app, Celery)

    def test_has_correct_name(self):
        from openmlr.celery_app import celery_app
        assert celery_app.main == "openmlr"

    def test_config_has_serializer(self):
        from openmlr.celery_app import celery_app
        assert celery_app.conf.task_serializer == "json"
        assert "json" in celery_app.conf.accept_content

    def test_config_has_timezone(self):
        from openmlr.celery_app import celery_app
        assert celery_app.conf.timezone == "UTC"
        assert celery_app.conf.enable_utc is True

    def test_config_worker_settings(self):
        from openmlr.celery_app import celery_app
        assert celery_app.conf.worker_prefetch_multiplier == 1
        assert celery_app.conf.task_acks_late is True

    def test_config_result_expiry(self):
        from openmlr.celery_app import celery_app
        assert celery_app.conf.result_expires == 3600

    def test_task_routing_configured(self):
        from openmlr.celery_app import celery_app
        routes = celery_app.conf.task_routes
        assert routes is not None

    def test_get_celery_app(self):
        from openmlr.celery_app import get_celery_app, celery_app
        assert get_celery_app() is celery_app
