"""IMAP response parsing helpers."""

import email
from email import policy

from custom_components.icloud_mcp.mail import (
    decode_utf7,
    encode_utf7,
    extract_body,
    parse_fetch,
    quote_mailbox,
)


def test_utf7_roundtrip() -> None:
    for name in ("INBOX", "Sent Messages", "Entwürfe", "日本語", "A&B", "Gelöschte Objekte"):
        assert decode_utf7(encode_utf7(name)) == name
    assert encode_utf7("A&B") == "A&-B"
    assert encode_utf7("Entwürfe") == "Entw&APw-rfe"
    assert quote_mailbox("Sent Messages") == '"Sent Messages"'


def test_parse_fetch_with_literals() -> None:
    header = b"From: Alice <alice@example.com>\r\nSubject: =?utf-8?q?Gr=C3=BC=C3=9Fe?=\r\nDate: Fri, 17 Oct 2026 10:00:00 +0200\r\nMessage-ID: <abc@example.com>\r\n\r\n"
    lines = [
        b"1 FETCH (UID 101 FLAGS (\\Seen) RFC822.SIZE 2048 BODY[HEADER.FIELDS (FROM SUBJECT DATE MESSAGE-ID)] {%d}"
        % len(header),
        bytearray(header),
        b")",
        b"2 FETCH (UID 102 FLAGS () RFC822.SIZE 10 BODY[HEADER.FIELDS (FROM SUBJECT DATE MESSAGE-ID)] {%d}"
        % len(header),
        header,
        b")",
        b"FETCH completed (0.001 + 0.000 secs).",
    ]
    items = parse_fetch(lines)
    assert [i.uid for i in items] == [101, 102]
    assert items[0].flags == ["\\Seen"]
    assert items[1].flags == []
    assert items[0].size == 2048
    assert items[0].literal() == header
    msg = email.message_from_bytes(items[0].literal(), policy=policy.compat32)
    assert msg["Message-ID"] == "<abc@example.com>"


def test_extract_body_prefers_plain_and_lists_attachments() -> None:
    raw = (
        b"From: a@b.c\r\nSubject: t\r\nMIME-Version: 1.0\r\n"
        b'Content-Type: multipart/mixed; boundary="X"\r\n\r\n'
        b'--X\r\nContent-Type: multipart/alternative; boundary="Y"\r\n\r\n'
        b"--Y\r\nContent-Type: text/plain; charset=utf-8\r\n\r\nHallo Welt\r\n"
        b"--Y\r\nContent-Type: text/html; charset=utf-8\r\n\r\n<p>Hallo <b>Welt</b></p>\r\n--Y--\r\n"
        b'--X\r\nContent-Type: application/pdf; name="a.pdf"\r\nContent-Disposition: attachment; filename="a.pdf"\r\n'
        b"Content-Transfer-Encoding: base64\r\n\r\nJVBERi0=\r\n--X--\r\n"
    )
    msg = email.message_from_bytes(raw, policy=policy.compat32)
    text, ctype, attachments = extract_body(msg)
    assert text.strip() == "Hallo Welt"
    assert ctype == "text/plain"
    assert attachments == [{"filename": "a.pdf", "content_type": "application/pdf", "size": 5}]
    html, ctype, _ = extract_body(msg, prefer_html=True)
    assert "<b>Welt</b>" in html


def test_extract_body_html_only_converted() -> None:
    raw = b"Content-Type: text/html; charset=utf-8\r\n\r\n<html><body><p>Zeile 1</p><p>Zeile&nbsp;2</p></body></html>"
    msg = email.message_from_bytes(raw, policy=policy.compat32)
    text, _, _ = extract_body(msg)
    assert text == "Zeile 1\n\nZeile\xa02"
