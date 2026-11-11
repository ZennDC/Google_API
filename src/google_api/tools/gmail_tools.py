from __future__ import annotations

import html
from collections.abc import Callable
from typing import Any

from ..gmail.handlers import LabelHandler, MessageHandler
from ..oauth.factory import GMAIL_SCOPES, get_gmail_service
from ._base import _BaseToolGroup
from ._utils import (
    TOOL_HANDLED_ERRORS,
    clamp_int,
    epoch_ms_to_iso,
    err,
    handle_tool_exception,
    looks_like_html,
    ok,
    strip_html,
    truncate_text,
)

_SYSTEM_LABELS = frozenset(
    {
        "INBOX",
        "STARRED",
        "IMPORTANT",
        "SENT",
        "DRAFT",
        "TRASH",
        "SPAM",
        "UNREAD",
        "CATEGORY_PERSONAL",
        "CATEGORY_SOCIAL",
        "CATEGORY_PROMOTIONS",
        "CATEGORY_UPDATES",
        "CATEGORY_FORUMS",
    }
)


def _resolve_existing_label_id(
    label_handler: LabelHandler, label_name: str
) -> str | None:
    label_id = label_handler.get_label_id(label_name)
    if label_id:
        return label_id
    upper_name = label_name.upper()
    if upper_name in _SYSTEM_LABELS and upper_name != label_name:
        return label_handler.get_label_id(upper_name)
    return None


class GmailTools(_BaseToolGroup):
    """Encapsulated, LLM-ready Gmail tools with OAuth lifecycle management."""

    def __init__(
        self,
        token_file: str | None = None,
        client_secret_file: str | None = None,
        headless: bool = False,
        save_token: bool = True,
        message_handler: MessageHandler | None = None,
        label_handler: LabelHandler | None = None,
        lock: Any | None = None,
        auth_callback: Callable[[], dict[str, Any] | None] | None = None,
    ) -> None:
        super().__init__(
            token_file=token_file,
            client_secret_file=client_secret_file,
            headless=headless,
            save_token=save_token,
            lock=lock,
            auth_callback=auth_callback,
        )
        self._message_handler = message_handler
        self._label_handler = label_handler
        self.is_authenticated = self._has_handlers()

    def _required_scopes(self) -> list[str]:
        return list(GMAIL_SCOPES)

    def _has_handlers(self) -> bool:
        return self._message_handler is not None and self._label_handler is not None

    def _build_handlers_from_credentials(self, creds: Any) -> None:
        if self._message_handler is None or self._label_handler is None:
            service = get_gmail_service(credentials=creds)
            if self._message_handler is None:
                self._message_handler = MessageHandler(service)
            if self._label_handler is None:
                self._label_handler = LabelHandler(service)

    def _iter_handlers(self) -> tuple[Any, ...]:
        return (self._message_handler, self._label_handler)

    def _clear_handlers(self) -> None:
        self._message_handler = None
        self._label_handler = None

    def get_tools(self) -> list[Callable[..., dict[str, Any]]]:
        """Returns the list of bound Gmail agent tool methods."""
        return [
            self.list_emails,
            self.read_email,
            self.send_email,
            self.apply_label,
            self.trash_email,
        ]

    def list_emails(
        self,
        query: str = "",
        max_results: int = 10,
        unread_only: bool = False,
    ) -> dict[str, Any]:
        """Searches Gmail and returns compact email summaries.

        Args:
            query: Gmail search query (e.g. 'from:alice@example.com subject:invoice').
            max_results: Maximum number of emails to return (1 to 50).
            unread_only: If True, only returns unread messages.

        Returns:
            Standard response dict containing 'count' and 'emails' metadata list.
        """
        with self._lock:
            auth_err = self._ensure_ready()
            if auth_err is not None:
                return auth_err
            assert self._message_handler is not None

            try:
                limit = clamp_int(max_results, 1, 50)
                effective_query = query.strip()
                if unread_only and "is:unread" not in effective_query.lower():
                    effective_query = f"is:unread {effective_query}".strip()

                msg_ids = self._message_handler.get_messages(
                    query=effective_query or None, max_results=limit
                )
                emails: list[dict[str, Any]] = []
                for msg_id in msg_ids:
                    msg = self._message_handler.get_message(msg_id, format="metadata")
                    snippet = html.unescape(msg.snippet).strip()
                    if len(snippet) > 200:
                        snippet = f"{snippet[:200].rstrip()}..."
                    emails.append(
                        {
                            "id": msg.id,
                            "thread_id": msg.thread_id,
                            "subject": msg.subject or "(No Subject)",
                            "sender": msg.sender or "",
                            "date": epoch_ms_to_iso(msg.internal_date),
                            "unread": "UNREAD" in msg.label_ids,
                            "snippet": snippet,
                        }
                    )

                return ok(
                    {"count": len(emails), "emails": emails},
                    f"Found {len(emails)} email(s).",
                )
            except TOOL_HANDLED_ERRORS as exc:
                return handle_tool_exception(exc, "Failed to list emails")

    def read_email(self, email_id: str, max_body_chars: int = 4000) -> dict[str, Any]:
        """Reads the full cleaned text content of a specific email by ID.

        Args:
            email_id: The Gmail message ID returned by list_emails.
            max_body_chars: Maximum character length of the returned body.

        Returns:
            Standard response dict with sender, subject, date, labels, and body.
        """
        with self._lock:
            auth_err = self._ensure_ready()
            if auth_err is not None:
                return auth_err
            assert self._message_handler is not None

            try:
                clean_id = email_id.strip()
                if not clean_id:
                    raise ValueError("email_id cannot be empty.")
                if max_body_chars <= 0:
                    raise ValueError("max_body_chars must be greater than 0.")

                msg = self._message_handler.get_message(clean_id, format="full")
                raw_body = msg.body or ""
                if looks_like_html(raw_body):
                    cleaned_body = strip_html(raw_body)
                else:
                    cleaned_body = html.unescape(raw_body).strip()

                body, truncated = truncate_text(cleaned_body, max_body_chars)
                return ok(
                    {
                        "id": msg.id,
                        "thread_id": msg.thread_id,
                        "subject": msg.subject or "(No Subject)",
                        "sender": msg.sender or "",
                        "date": epoch_ms_to_iso(msg.internal_date),
                        "labels": list(msg.label_ids),
                        "body": body,
                        "truncated": truncated,
                    },
                    "Email retrieved.",
                )
            except TOOL_HANDLED_ERRORS as exc:
                return handle_tool_exception(exc, f"Failed to read email '{email_id}'")

    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        cc: str = "",
        thread_id: str = "",
        save_as_draft: bool = False,
    ) -> dict[str, Any]:
        """Sends an email or saves it as a draft.

        Args:
            to: Recipient email address (comma-separated for multiple recipients).
            subject: Email subject line.
            body: Plain-text email body.
            cc: Optional CC email address(es), comma-separated.
            thread_id: Optional Gmail thread ID to reply within an existing thread.
            save_as_draft: If True, saves as a draft instead of sending immediately.

        Returns:
            Standard response dict with created message or draft ID and metadata.
        """
        with self._lock:
            auth_err = self._ensure_ready()
            if auth_err is not None:
                return auth_err
            assert self._message_handler is not None

            try:
                recipients = [addr.strip() for addr in to.split(",") if addr.strip()]
                if not recipients:
                    raise ValueError("Recipient 'to' cannot be empty.")

                cc_list = [addr.strip() for addr in cc.split(",") if addr.strip()]
                to_arg: str | list[str] = (
                    recipients[0] if len(recipients) == 1 else recipients
                )
                cc_arg: str | list[str] | None = (
                    cc_list[0] if len(cc_list) == 1 else (cc_list or None)
                )
                tid = thread_id.strip() or None

                if save_as_draft:
                    res = self._message_handler.create_draft(
                        to=to_arg,
                        subject=subject,
                        body=body,
                        cc=cc_arg,
                        thread_id=tid,
                    )
                    nested_msg = res.get("message")
                    out_thread_id = (
                        nested_msg.get("threadId", "")
                        if isinstance(nested_msg, dict)
                        else res.get("threadId", "")
                    )
                    return ok(
                        {
                            "id": res.get("id", ""),
                            "thread_id": out_thread_id,
                            "to": ", ".join(recipients),
                            "subject": subject,
                            "draft": True,
                        },
                        "Draft created successfully.",
                    )

                res = self._message_handler.send_message(
                    to=to_arg,
                    subject=subject,
                    body=body,
                    cc=cc_arg,
                    thread_id=tid,
                )
                return ok(
                    {
                        "id": res.get("id", ""),
                        "thread_id": res.get("threadId", ""),
                        "to": ", ".join(recipients),
                        "subject": subject,
                        "draft": False,
                    },
                    "Email sent successfully.",
                )
            except TOOL_HANDLED_ERRORS as exc:
                return handle_tool_exception(exc, "Failed to send email")

    def apply_label(
        self,
        email_id: str,
        label_name: str,
        remove: bool = False,
    ) -> dict[str, Any]:
        """Applies or removes a Gmail label on an email by label name.

        Args:
            email_id: The Gmail message ID to modify.
            label_name: Human-readable label name (created automatically when applying if missing).
            remove: If True, removes the label instead of applying it.

        Returns:
            Standard response dict confirming the applied or removed label.
        """
        with self._lock:
            auth_err = self._ensure_ready()
            if auth_err is not None:
                return auth_err
            assert self._label_handler is not None

            try:
                clean_id = email_id.strip()
                clean_label = label_name.strip()
                if not clean_id:
                    raise ValueError("email_id cannot be empty.")
                if not clean_label:
                    raise ValueError("label_name cannot be empty.")

                existing_id = _resolve_existing_label_id(
                    self._label_handler, clean_label
                )

                if remove:
                    if not existing_id:
                        return err(f"Label '{clean_label}' not found.", "NOT_FOUND")
                    self._label_handler.remove_label_from_message(clean_id, existing_id)
                    return ok(
                        {
                            "email_id": clean_id,
                            "label_name": clean_label,
                            "label_id": existing_id,
                            "action": "removed",
                        },
                        f"Removed label '{clean_label}'.",
                    )

                label_id = existing_id or self._label_handler.get_or_create_label_id(
                    clean_label
                )
                self._label_handler.add_label_to_message(clean_id, label_id)
                return ok(
                    {
                        "email_id": clean_id,
                        "label_name": clean_label,
                        "label_id": label_id,
                        "action": "added",
                    },
                    f"Applied label '{clean_label}'.",
                )
            except TOOL_HANDLED_ERRORS as exc:
                return handle_tool_exception(exc, "Failed to update label")

    def trash_email(self, email_id: str) -> dict[str, Any]:
        """Moves an email to Gmail trash (reversible).

        Args:
            email_id: The Gmail message ID to move to trash.

        Returns:
            Standard response dict confirming the trashed email ID.
        """
        with self._lock:
            auth_err = self._ensure_ready()
            if auth_err is not None:
                return auth_err
            assert self._message_handler is not None

            try:
                clean_id = email_id.strip()
                if not clean_id:
                    raise ValueError("email_id cannot be empty.")

                self._message_handler.trash_message(clean_id)
                return ok({"id": clean_id}, "Email moved to trash.")
            except TOOL_HANDLED_ERRORS as exc:
                return handle_tool_exception(exc, f"Failed to trash email '{email_id}'")
