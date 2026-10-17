"""vCard parsing/serialising."""

from custom_components.friedafetch.carddav_client import apply_contact_fields
from custom_components.friedafetch.vcard import VCard

ICLOUD_VCARD = """BEGIN:VCARD
VERSION:3.0
PRODID:-//Apple Inc.//iCloud Web Address Book 2410B35//EN
N:Mustermann;Max;Peter;Dr.;
FN:Dr. Max Peter Mustermann
NICKNAME:Maxi
ORG:Beispiel GmbH;Entwicklung
TITLE:CTO
EMAIL;type=INTERNET;type=HOME;type=pref:max@example.com
item1.EMAIL;type=INTERNET:max.work@example.org
item1.X-ABLabel:_$!<Work>!$_
TEL;type=CELL;type=VOICE;type=pref:+49 170 1234567
TEL;type=HOME;type=VOICE:+49 30 123456
item2.ADR;type=HOME;type=pref:;;Musterstraße 1;Berlin;;10115;Deutschland
item2.X-ABADR:de
BDAY;value=date:1980-05-12
NOTE:Mag Kaffee\\, keinen Tee\\;\\nZweite Zeile
PHOTO;ENCODING=b;TYPE=JPEG:/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0a
 HBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIy
UID:A1B2C3D4-0000-1111-2222-333344445555
REV:2026-01-01T00:00:00Z
END:VCARD
"""


def test_parse_icloud_vcard() -> None:
    card = VCard.parse(ICLOUD_VCARD)
    data = card.to_dict()
    assert data["uid"] == "A1B2C3D4-0000-1111-2222-333344445555"
    assert data["full_name"] == "Dr. Max Peter Mustermann"
    assert data["given_name"] == "Max"
    assert data["family_name"] == "Mustermann"
    assert data["prefix"] == "Dr."
    assert data["organization"] == "Beispiel GmbH"
    assert data["department"] == "Entwicklung"
    assert data["emails"] == [
        {"label": "home", "value": "max@example.com", "preferred": True},
        {"label": "work", "value": "max.work@example.org", "preferred": False},
    ]
    assert data["phones"][0] == {"label": "cell", "value": "+49 170 1234567", "preferred": True}
    assert data["addresses"][0]["street"] == "Musterstraße 1"
    assert data["addresses"][0]["postal_code"] == "10115"
    assert data["birthday"] == "1980-05-12"
    assert data["note"] == "Mag Kaffee, keinen Tee;\nZweite Zeile"
    assert "raw" not in data


def test_roundtrip_preserves_unknown_properties() -> None:
    card = VCard.parse(ICLOUD_VCARD)
    out = card.serialize()
    assert "PHOTO;ENCODING=b;TYPE=JPEG:" in out
    assert "X-ABADR:de" in out
    assert out.startswith("BEGIN:VCARD\r\nVERSION:3.0\r\n")
    assert out.endswith("END:VCARD\r\n")
    # folding keeps lines <= 75 octets
    for line in out.split("\r\n"):
        assert len(line.encode()) <= 75
    again = VCard.parse(out)
    assert again.to_dict() == card.to_dict()


def test_matches() -> None:
    card = VCard.parse(ICLOUD_VCARD)
    assert card.matches("muster")
    assert card.matches("max@example")
    assert card.matches("0170 1234567")
    assert card.matches("beispiel gmbh")
    assert card.matches("Max Mustermann")
    assert not card.matches("Schmidt")


def test_apply_fields_replaces_lists_and_keeps_rest() -> None:
    card = VCard.parse(ICLOUD_VCARD)
    apply_contact_fields(
        card,
        {
            "emails": [{"value": "new@example.com", "label": "Privat"}],
            "note": "",
            "given_name": "Maximilian",
            "birthday": "1981-01-02",
        },
    )
    data = card.to_dict()
    assert data["emails"] == [{"label": "privat", "value": "new@example.com", "preferred": False}]
    assert data["note"] is None
    assert data["given_name"] == "Maximilian"
    assert data["full_name"] == "Dr. Maximilian Peter Mustermann"
    assert data["birthday"] == "1981-01-02"
    # phones untouched, orphaned item1 label removed
    assert len(data["phones"]) == 2
    out = card.serialize()
    assert "_$!<Work>!$_" not in out  # orphaned label of the removed work e-mail is gone
    assert "X-ABLabel:Privat" in out
    assert "max.work@example.org" not in out


def test_new_card_needs_fn() -> None:
    card = VCard()
    card.ensure_uid()
    apply_contact_fields(card, {"organization": "ACME", "emails": ["info@acme.test"]})
    data = card.to_dict()
    assert data["full_name"] == "ACME"
    assert data["emails"][0]["value"] == "info@acme.test"
    assert card.uid
