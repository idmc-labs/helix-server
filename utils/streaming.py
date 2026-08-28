import contextlib
import json
import typing

from django.core.serializers.json import DjangoJSONEncoder

from utils.common import get_temp_file


def _dumps(value: typing.Any, encoder: typing.Type[json.JSONEncoder]) -> bytes:
    return json.dumps(value, cls=encoder).encode("utf-8")


def stream_json_array(
    items: typing.Iterable[typing.Any],
    encoder: typing.Type[json.JSONEncoder] = DjangoJSONEncoder,
) -> typing.Iterator[bytes]:
    """Yield a JSON array as UTF-8 byte chunks, one element at a time.

    Use together with a queryset ``.iterator()`` so neither the database rows
    nor the encoded payload are fully materialised.
    """
    yield b"["
    first = True
    for item in items:
        if first:
            first = False
        else:
            yield b","
        yield _dumps(item, encoder)
    yield b"]"


def stream_json_object_with_array(
    *,
    scalar_fields: dict,
    array_key: str,
    items: typing.Iterable[typing.Any],
    encoder: typing.Type[json.JSONEncoder] = DjangoJSONEncoder,
) -> typing.Iterator[bytes]:
    """Yield ``{<scalar_fields>, "<array_key>": [<item>, ...]}`` as UTF-8 byte
    chunks, streaming the array field one element at a time.

    ``scalar_fields`` are the small, fixed top-level keys (for GeoJSON:
    ``type``, ``readme``, ``lastUpdated``).
    """
    # Emit the fixed fields as an object, then reopen it to append the array.
    scalar_chunk = _dumps(scalar_fields, encoder)
    # scalar_chunk always ends with "}"; drop it so we can append more keys.
    yield scalar_chunk[:-1]

    separator = b"," if scalar_fields else b""
    yield separator + _dumps(array_key, encoder) + b":"
    yield from stream_json_array(items, encoder)
    yield b"}"


@contextlib.contextmanager
def spool_to_temp_file(chunks: typing.Iterable[bytes]) -> typing.Generator[typing.IO[bytes], None, None]:
    """Write a byte-chunk iterator to a temp file and yield it rewound.

    A seekable temp file is the well-worn input for ``Storage.save``/boto3 —
    no reliance on storage-backend internals — and persisting only after the
    iterator is fully consumed means a mid-generation failure never publishes
    a truncated object. The temp file is removed on exit.
    """
    with get_temp_file() as tmp:
        for chunk in chunks:
            tmp.write(chunk)
        tmp.flush()
        tmp.seek(0)
        yield tmp
