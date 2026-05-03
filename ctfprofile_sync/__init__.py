"""
CTFProfile Sync — CTFd plugin

Pushes CTFd data to a CTFProfile instance in real-time.
Adds an admin panel at /admin/ctfprofile/ for configuration.

Installation
------------
Copy or symlink this package into CTFd's ``CTFd/plugins/`` directory so that
CTFd discovers and loads it automatically on startup.
"""

from __future__ import annotations

import logging

from sqlalchemy import event as sa_event  # type: ignore

log = logging.getLogger(__name__)


def load(app):
    """Entry-point called by CTFd when the plugin is loaded."""
    from .routes import blueprint
    app.register_blueprint(blueprint)

    # Register the live solve listener
    try:
        from CTFd.models import Solves  # type: ignore
        sa_event.listen(Solves, "after_insert", _on_solve, propagate=True)
        log.info("CTFProfile Sync: solve listener registered.")
    except Exception as exc:
        log.warning("CTFProfile Sync: could not attach solve listener: %s", exc)

    log.info("CTFProfile Sync plugin loaded. Admin panel: /admin/ctfprofile/")


# ---------------------------------------------------------------------------
# SQLAlchemy event listener
# ---------------------------------------------------------------------------

def _on_solve(mapper, connection, target):
    """
    Fired after a new row is inserted into the Solves table.

    Runs synchronously in the request cycle; kept fast by sending only the
    minimal single-solve payload rather than a full re-sync.
    """
    try:
        from . import config as cfg
        conf = cfg.get_all()
        if conf.get("ctfprofile_sync_on_solve") != "1":
            return
        if not conf.get("ctfprofile_url") or not conf.get("ctfprofile_api_key") or not conf.get("ctfprofile_event_slug"):
            return

        from .api import CTFProfileClient, CTFProfileAPIError
        from .sync import build_solve_payload

        payload = build_solve_payload(target)
        client = CTFProfileClient(
            conf["ctfprofile_url"],
            conf["ctfprofile_api_key"],
            conf["ctfprofile_event_slug"],
        )
        client.sync(payload)
    except Exception as exc:
        # Never let sync errors propagate into CTFd's solve submission flow
        log.warning("CTFProfile Sync: live solve push failed: %s", exc)
