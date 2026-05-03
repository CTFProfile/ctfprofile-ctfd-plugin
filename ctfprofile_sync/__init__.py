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

    # Create the "CTFProfile ID" custom user field if it doesn't exist yet.
    # This surfaces on every user's CTFd profile settings page so they can
    # enter their CTFProfile public ID for precise account linking.
    with app.app_context():
        _ensure_user_field()

    log.info("CTFProfile Sync plugin loaded. Admin panel: /admin/ctfprofile/")


def _ensure_user_field():
    """
    Create a 'CTFProfile Linking Token' text field in CTFd's user-profile
    fields table if one doesn't already exist.

    This field is shown on every user's Settings page so they can paste in
    their private CTFProfile linking token.  The token is NOT the same as
    the public CTFProfile ID — it is a secret credential specific to the
    CTFd integration and is only visible in the user's own CTFProfile
    Account Settings page.
    """
    try:
        from CTFd.models import UserFields, db  # type: ignore
        existing = UserFields.query.filter_by(name="CTFProfile Linking Token").first()
        if not existing:
            field = UserFields(
                name="CTFProfile Linking Token",
                description=(
                    "Your private CTFProfile linking token. "
                    "Find it in CTFProfile → Profile → Account Settings → "
                    "\"CTFd linking token\". "
                    "This is NOT your public CTFProfile ID — it is a private secret. "
                    "Do not share it. Setting this ensures your CTFd solves are credited "
                    "to the correct CTFProfile account even if your usernames differ."
                ),
                field_type="text",
                required=False,
                public=False,   # private — not shown on public CTFd profiles
                editable=True,
            )
            db.session.add(field)
            db.session.commit()
            log.info("CTFProfile Sync: created 'CTFProfile Linking Token' user field.")
    except Exception as exc:
        log.warning("CTFProfile Sync: could not create user field: %s", exc)


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
