"""Bind spoken consent to the exact runtime request visible in the overlay."""
from __future__ import annotations

import re

from app.autonomy.approvals import ApprovalStatus


class VoicePermissionDialog:
    """Only live, displayed requests can be approved; model output is never consent."""

    def __init__(self, approvals, show_question, dismiss_question, *, show_status=None, close_overlay=None) -> None:
        self.approvals = approvals
        self._show = show_question
        self._dismiss = dismiss_question
        self._show_status = show_status
        self._close = close_overlay or dismiss_question
        self.enabled = False
        self._displayed_id: str | None = None
        self._question: str | None = None
        self._conversation_question: str | None = None
        approvals.on_requested = self.requested
        approvals.on_resolved = self.resolved

    @property
    def current_question(self) -> str | None:
        return self._question if self.enabled else None

    @property
    def pending(self) -> bool:
        return self.current_question is not None

    @property
    def request_id(self) -> str | None:
        return self._displayed_id if self.pending else None

    def start(self) -> None:
        self.enabled = True
        self._refresh()
        self.status("Listening. Tell me what you would like to do.")

    def stop(self) -> None:
        self.enabled = False
        self.cancel_pending()
        self._conversation_question = None
        self._close()

    def status(self, message: str) -> None:
        if self.enabled and not self.pending and not self._conversation_question and self._show_status:
            self._show_status(message)

    def cancel_pending(self) -> None:
        for request in self.approvals.pending():
            try:
                self.approvals.decide(request.approval_id, ApprovalStatus.DENIED, "voice_cancelled")
            except (KeyError, ValueError):
                pass  # A simultaneous dashboard decision is authoritative.
        self._displayed_id = None
        self._question = None

    def show_conversation(self, question: str) -> None:
        self._conversation_question = question
        if not self.pending:
            self._show(question)

    def dismiss_conversation(self) -> None:
        self._conversation_question = None
        if not self.pending:
            self._dismiss()

    def requested(self, _request) -> None:
        self._refresh()

    def resolved(self, _request) -> None:
        self._refresh()

    def _refresh(self) -> None:
        if not self.enabled:
            self._displayed_id = None
            self._question = None
            return
        requests = self.approvals.pending()
        request = next((item for item in requests if item.approval_id == self._displayed_id), None)
        if request is None:
            request = next(iter(requests), None)
        if request is None:
            had_question = self._question is not None
            self._displayed_id = None
            self._question = None
            if had_question:
                if self._conversation_question:
                    self._show(self._conversation_question)
                else:
                    self._dismiss()
            return
        if request.approval_id == self._displayed_id:
            return
        permissions = ", ".join(request.permissions or (request.permission,))
        question = f"Allow {request.tool} to use {permissions}? {request.reason[:300]} "
        if request.can_remember:
            question += ("Say 'yes, continue' to allow and remember permission for this tool on this computer, "
                         "'allow once' for this task, or 'no' to deny.")
        else:
            question += "Say 'yes, continue' to allow this action once, or 'no' to deny."
        # Only mark it approvable after presentation succeeds.
        self._show(question)
        self._displayed_id = request.approval_id
        self._question = question

    def respond(self, transcript: str, *, allow_execution: bool,
                confidence: float, minimum_confidence: float,
                request_id: str | None = None) -> dict | None:
        if not self.pending:
            if request_id:
                return {"status": "waiting", "mission_id": None,
                        "result": "That permission request has already ended. Please repeat your task."}
            return None
        if request_id is not None and request_id != self._displayed_id:
            return {"status": "waiting", "mission_id": None,
                    "result": "Please answer the permission request now shown in the overlay.",
                    "question": self._question}
        request_id = self._displayed_id
        request = next((item for item in self.approvals.pending()
                        if item.approval_id == request_id), None)
        if request is None:
            self._refresh()
            return {"status": "waiting", "mission_id": None,
                    "result": "That permission request has already ended. Please repeat your task."}
        normalized = re.sub(r"[^a-z0-9]+", " ", transcript.casefold()).strip()
        approve = {"yes", "yeah", "yes continue", "yeah continue", "continue", "approve",
                   "allow", "yes please", "go ahead", "yes go ahead", "okay", "ok",
                   "allow and remember", "yes remember", "allow once", "just this once"}
        deny = {"no", "no thanks", "deny", "cancel", "cancel it", "do not allow", "don t allow"}
        if (not allow_execution or confidence < minimum_confidence
                or normalized not in approve | deny):
            self._show(self._question)
            return {"status": "waiting", "mission_id": request.mission_id,
                    "result": "Please say 'yes, continue', 'allow once', or 'no' for the displayed permission.",
                    "question": self._question}
        accepted = normalized in approve
        remember = accepted and request.can_remember and normalized not in {"allow once", "just this once"}
        try:
            decision = self.approvals.decide(request_id,
                ApprovalStatus.APPROVED if accepted else ApprovalStatus.DENIED,
                "voice_user", remember=remember)
            remember = decision.remembered
        except (KeyError, ValueError):
            self._refresh()
            return {"status": "waiting", "mission_id": request.mission_id,
                    "result": "That permission request has already ended."}
        except OSError:
            return {"status": "waiting", "mission_id": request.mission_id,
                    "result": "I couldn't save the permission decision. The action is still waiting; "
                              "check access to the application's data folder.",
                    "question": self._question}
        return {"status": "completed", "mission_id": request.mission_id,
                "result": ("Permission saved; continuing the task." if remember else
                           "Permission allowed once; continuing the task." if accepted else
                           "Permission denied; the action was not executed.")}
