"""
Admin blueprint: /admin/ctfprofile/

Routes
------
GET  /admin/ctfprofile/           — Settings page
POST /admin/ctfprofile/save       — Save settings
POST /admin/ctfprofile/test       — Test connectivity
POST /admin/ctfprofile/full-sync  — Push full CTFd state to CTFProfile
"""

from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for  # type: ignore
from CTFd.utils.decorators import admins_only  # type: ignore

from . import config as cfg
from .api import CTFProfileClient, CTFProfileAPIError
from .sync import build_full_payload

blueprint = Blueprint(
    "ctfprofile_sync",
    __name__,
    template_folder="templates",
    url_prefix="/admin/ctfprofile",
)


@blueprint.route("/", methods=["GET"])
@admins_only
def settings():
    conf = cfg.get_all()
    return render_template("ctfprofile_sync/settings.html", **conf)


@blueprint.route("/save", methods=["POST"])
@admins_only
def save():
    data = {
        "ctfprofile_url": (request.form.get("ctfprofile_url") or "").strip().rstrip("/"),
        "ctfprofile_api_key": (request.form.get("ctfprofile_api_key") or "").strip(),
        "ctfprofile_event_slug": (request.form.get("ctfprofile_event_slug") or "").strip(),
        "ctfprofile_sync_on_solve": "1" if request.form.get("ctfprofile_sync_on_solve") else "0",
    }
    cfg.save(data)
    flash("CTFProfile settings saved.", "success")
    return redirect(url_for("ctfprofile_sync.settings"))


@blueprint.route("/test", methods=["POST"])
@admins_only
def test_connection():
    conf = cfg.get_all()
    if not conf.get("ctfprofile_url") or not conf.get("ctfprofile_api_key") or not conf.get("ctfprofile_event_slug"):
        flash("Please save your CTFProfile URL, API key, and event slug first.", "warning")
        return redirect(url_for("ctfprofile_sync.settings"))

    client = CTFProfileClient(
        conf["ctfprofile_url"],
        conf["ctfprofile_api_key"],
        conf["ctfprofile_event_slug"],
    )
    try:
        result = client.test()
        flash(f"Connection successful! Response: {result}", "success")
    except CTFProfileAPIError as exc:
        flash(f"Connection failed: {exc}", "danger")

    return redirect(url_for("ctfprofile_sync.settings"))


@blueprint.route("/full-sync", methods=["POST"])
@admins_only
def full_sync():
    conf = cfg.get_all()
    if not conf.get("ctfprofile_url") or not conf.get("ctfprofile_api_key") or not conf.get("ctfprofile_event_slug"):
        flash("Please configure CTFProfile settings first.", "warning")
        return redirect(url_for("ctfprofile_sync.settings"))

    client = CTFProfileClient(
        conf["ctfprofile_url"],
        conf["ctfprofile_api_key"],
        conf["ctfprofile_event_slug"],
    )
    try:
        payload = build_full_payload()
        result = client.sync(payload)
        summary = result.get("summary", {})
        parts = [f"{v} {k.replace('_', ' ')}" for k, v in summary.items() if v]
        flash("Full sync complete. " + (", ".join(parts) if parts else "No changes."), "success")
    except CTFProfileAPIError as exc:
        flash(f"Sync failed: {exc}", "danger")
    except Exception as exc:
        flash(f"Unexpected error during sync: {exc}", "danger")

    return redirect(url_for("ctfprofile_sync.settings"))
