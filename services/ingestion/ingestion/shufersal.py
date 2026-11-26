import gzip
import re
import zlib
from datetime import datetime
from decimal import Decimal
from io import BytesIO
from xml.etree import ElementTree as ET

from .models import PriceObservation, Retailer, SourceProduct, Store

MAX_XML_BYTES = 32 * 1024 * 1024


def field(node: ET.Element, tag: str) -> str:
    values = node.findall(tag)
    if len(values) != 1 or len(values[0]):
        raise ValueError(f"{tag}: expected exactly one scalar field")
    value = (values[0].text or "").strip()
    if not value or "\ufffd" in value:
        raise ValueError(f"{tag}: missing text or replacement character")
    return value


def identifier(node: ET.Element, tag: str) -> str:
    value = field(node, tag)
    if not re.fullmatch(r"[0-9]+", value):
        raise ValueError(f"{tag}: expected ASCII digits")
    return value


def number(node: ET.Element, tag: str, *, positive: bool = False) -> Decimal:
    value = field(node, tag)
    pattern = r"[0-9]+(?:\.[0-9]+)?" if positive else r"[0-9]+(?:\.[0-9]{1,2}0*)?"
    if not re.fullmatch(pattern, value):
        raise ValueError(f"{tag}: invalid decimal")
    result = Decimal(value)
    if positive and result <= 0:
        raise ValueError(f"{tag}: expected a positive quantity")
    return result


def xml_root(payload: bytes) -> ET.Element:
    if payload.startswith(b"\x1f\x8b"):
        try:
            with gzip.GzipFile(fileobj=BytesIO(payload)) as stream:
                payload = stream.read(MAX_XML_BYTES + 1)
        except (OSError, EOFError, zlib.error) as exc:
            raise ValueError("invalid gzip") from exc
    if len(payload) > MAX_XML_BYTES:
        raise ValueError("XML exceeds size limit")
    try:
        xml = payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("expected UTF-8 XML") from exc
    declaration = re.match(r"<\?xml\s+[^?]*encoding\s*=\s*(['\"])([^'\"]+)\1", xml)
    if declaration and declaration[2].lower() != "utf-8":
        raise ValueError("unsupported XML encoding declaration")
    if "\x00" in xml or re.search(r"<!DOCTYPE", xml):
        raise ValueError("XML contains NUL or a DTD")
    try:
        return ET.fromstring(xml)
    except ET.ParseError as exc:
        raise ValueError(f"malformed XML: {exc}") from exc


def parse(payload: bytes) -> tuple[Store, tuple[PriceObservation, ...]]:
    root = xml_root(payload)
    containers = root.findall("Items")
    if root.tag != "Root" or len(containers) != 1:
        raise ValueError("expected Shufersal Root/Items")
    retailer = Retailer("shufersal", identifier(root, "ChainID"))
    store = Store(retailer, identifier(root, "SubChainID"), identifier(root, "StoreID"))
    observations = []
    seen: set[tuple[str, str]] = set()
    for row, item in enumerate(containers[0], start=1):
        try:
            if item.tag != "Item":
                raise ValueError("expected Item")
            product = SourceProduct(
                retailer,
                identifier(item, "ItemType"),
                identifier(item, "ItemCode"),
                field(item, "ItemName"),
                number(item, "Quantity", positive=True),
                field(item, "UnitQty"),
            )
            if product.key in seen:
                raise ValueError("duplicate source product")
            updated_at = field(item, "PriceUpdateTime")
            if not re.fullmatch(
                r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}", updated_at
            ):
                raise ValueError("PriceUpdateTime: expected local ISO timestamp")
            observations.append(
                PriceObservation(
                    store,
                    product,
                    number(item, "ItemPrice"),
                    datetime.fromisoformat(updated_at),
                    row,
                    identifier(item, "ItemStatus"),
                )
            )
            seen.add(product.key)
        except ValueError as exc:
            raise ValueError(f"row {row}: {exc}") from exc
    return store, tuple(observations)
