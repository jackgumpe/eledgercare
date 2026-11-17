"""New runtime wiring; accepted protocol and all older namespaces stay read-only."""
from pathlib import Path
from qualification.mapping_v1.common import (ROOT, BASELINE, BASELINE_TREE, norm, parse_native, ParseError,
    sha, git, tree, load_json, write, safe_repo_path, mapping, score_document, summarize)
from .protocol.common import verify_pins

HERE = Path(__file__).resolve().parent
MAPPING_TREE = '59f66d0d3d9be145a43efcc9258eb260d3ef2f00'
PROTOCOL_SOURCE = '6207daf1dc9cbdd141d083ca2d8d1e7507c63b09'


def protocol():
    return load_json(HERE / 'runtime_protocol.json')


def verify_frozen_mappers():
    verify_pins()
    for path in ('qualification/mapping_v2/protocol', 'qualification/mapping_v2/README.md', 'qualification/mapping_v2/__init__.py'):
        if tree('HEAD', path) != tree(PROTOCOL_SOURCE, path) or git('diff', 'HEAD', '--', path).strip():
            raise PermissionError('Accepted public protocol changed: ' + path)
