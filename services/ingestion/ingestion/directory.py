from hashlib import sha256
from urllib.parse import urlsplit

from .models import Retailer, Store, StoreDirectory, StoreLocation
from .xmlfeed import digits, elements, field, identifier, scalar


def public_url(source_url: str) -> str:
    url = urlsplit(source_url)
    return url._replace(
        netloc=url.netloc.rsplit("@", 1)[-1], query="", fragment=""
    ).geturl()


def read_directory(
    payload: bytes,
    source_url: str,
    source: str,
    root: str,
    *,
    allow_utf16: bool = False,
) -> StoreDirectory:
    subchains = (root, "SubChains")
    retailer: Retailer | None = None
    name: str | None = None
    locations: dict[tuple[Retailer, str, str], StoreLocation] = {}
    containers = 0
    selected = {(root, tag) for tag in ("ChainID", "ChainName")} | {subchains + ("*",)}
    for path, node in elements(
        payload, selected, watch={subchains}, allow_utf16=allow_utf16
    ):
        if path[0] != root:
            raise ValueError(f"expected {source} {root}/SubChains")
        if path == (root, "ChainID"):
            if retailer is not None:
                raise ValueError("duplicate ChainID")
            retailer = Retailer(source, digits(scalar(node), "ChainID"))
        elif path == (root, "ChainName"):
            if name is not None:
                raise ValueError("duplicate ChainName")
            name = scalar(node)
        elif path == subchains:
            containers += 1
        elif len(path) == 3 and path[:2] == subchains:
            if node.tag != "SubChain":
                raise ValueError("expected SubChain")
            if retailer is None:
                raise ValueError("missing ChainID before SubChains")
            subchain = identifier(node, "SubChainID")
            groups = node.findall("Stores")
            if len(groups) != 1:
                raise ValueError("expected exactly one Stores container")
            for row in groups[0]:
                if row.tag != "Store":
                    raise ValueError("expected Store")
                store = Store(retailer, subchain, identifier(row, "StoreID"))
                if store.directory_key in locations:
                    raise ValueError("duplicate store identifiers")
                locations[store.directory_key] = StoreLocation(
                    store,
                    field(row, "StoreName"),
                    field(row, "Address", optional=True) or None,
                    field(row, "City", optional=True) or None,
                    field(row, "ZIPCode", optional=True) or None,
                )
    if retailer is None or name is None or containers != 1:
        raise ValueError(f"expected {source} directory header and SubChains")
    return StoreDirectory(
        retailer,
        name,
        tuple(locations.values()),
        public_url(source_url),
        sha256(payload).hexdigest(),
    )
