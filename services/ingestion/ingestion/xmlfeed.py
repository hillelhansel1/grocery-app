import gzip
import re
import zlib
from collections.abc import Iterator, Set
from contextlib import ExitStack
from decimal import Decimal
from io import BytesIO, TextIOWrapper
from typing import cast
from xml.etree import ElementTree as ET

MAX_XML_BYTES = 32 * 1024 * 1024


def elements(
    payload: bytes,
    keep: Set[tuple[str, ...]],
    *,
    watch: Set[tuple[str, ...]],
    allow_utf16: bool = False,
) -> Iterator[tuple[tuple[str, ...], ET.Element]]:
    """Yield selected end events, releasing each element when its consumer advances."""
    with ExitStack() as stack:
        source: BytesIO | gzip.GzipFile = stack.enter_context(BytesIO(payload))
        if payload.startswith(b"\x1f\x8b"):
            source = stack.enter_context(gzip.GzipFile(fileobj=source))
        try:
            prefix = (
                source.peek(2) if isinstance(source, gzip.GzipFile) else payload[:2]
            )
            utf16 = allow_utf16 and prefix.startswith((b"\xff\xfe", b"\xfe\xff"))
            encoding = "utf-16" if utf16 else "utf-8"
            reader = stack.enter_context(
                TextIOWrapper(
                    source, encoding=encoding if utf16 else "utf-8-sig", newline=""
                )
            )
            parser = ET.XMLPullParser(events=("start", "end"))
            nodes: list[ET.Element] = []
            path: list[str] = []
            tail = ""
            size = 0
            while chunk := reader.read(16384):
                if not size and chunk.startswith("<?xml"):
                    declaration, separator, _ = chunk.partition("?>")
                    match = re.search(
                        r"\bencoding\s*=\s*(['\"])([^'\"]+)\1", declaration
                    )
                    if not separator or (match and match[2].lower() != encoding):
                        raise ValueError("unsupported XML encoding declaration")
                size += len(chunk.encode(encoding.replace("utf-16", "utf-16-le")))
                if size > MAX_XML_BYTES:
                    raise ValueError("XML exceeds size limit")
                if "\x00" in chunk or "<!DOCTYPE" in tail + chunk:
                    raise ValueError("XML contains NUL or a DTD")
                tail = chunk[-8:]
                parser.feed(chunk)
                events = cast(
                    "Iterator[tuple[str, ET.Element[str]]]", parser.read_events()
                )
                for event, node in events:
                    if event == "start":
                        nodes.append(node)
                        path.append(node.tag)
                        continue
                    location = tuple(path)
                    if (
                        selected(location, keep)
                        or location in watch
                        or len(location) == 1
                    ):
                        yield location, node
                    nodes.pop()
                    path.pop()
                    if nodes and not any(
                        selected(location[:i], keep) for i in range(1, len(location))
                    ):
                        nodes[-1].remove(node)
                        node.clear()
            parser.close()
        except UnicodeDecodeError as exc:
            raise ValueError("expected UTF-8 XML or permitted UTF-16 BOM") from exc
        except (OSError, EOFError, zlib.error) as exc:
            raise ValueError("invalid gzip") from exc
        except ET.ParseError as exc:
            raise ValueError(f"malformed XML: {exc}") from exc


def selected(path: tuple[str, ...], keep: Set[tuple[str, ...]]) -> bool:
    return path in keep or path[:-1] + ("*",) in keep


def field(node: ET.Element, tag: str, *, optional: bool = False) -> str:
    values = node.findall(tag)
    if not values and optional:
        return ""
    if len(values) != 1 or len(values[0]):
        raise ValueError(f"{tag}: expected exactly one scalar field")
    return scalar(values[0], optional=optional)


def scalar(node: ET.Element, *, optional: bool = False) -> str:
    value = (node.text or "").strip()
    if len(node) or "\ufffd" in value or (not optional and not value):
        raise ValueError(f"{node.tag}: missing text or replacement character")
    return value


def digits(value: str, tag: str) -> str:
    if not re.fullmatch(r"[0-9]+", value):
        raise ValueError(f"{tag}: expected ASCII digits")
    return value


def identifier(node: ET.Element, tag: str) -> str:
    return digits(field(node, tag), tag)


def number(node: ET.Element, tag: str, *, positive: bool = False) -> Decimal:
    value = field(node, tag)
    pattern = r"[0-9]+(?:\.[0-9]+)?" if positive else r"[0-9]+(?:\.[0-9]{1,2}0*)?"
    if not re.fullmatch(pattern, value):
        raise ValueError(f"{tag}: invalid decimal")
    result = Decimal(value)
    if positive and result <= 0:
        raise ValueError(f"{tag}: expected a positive quantity")
    return result
