"""Pinned read-only reuse of accepted B0/v1 primitives."""
import json
from pathlib import Path
from qualification.mapping_v1.common import (ROOT,sha,git,tree,load_json,write,safe_repo_path,
    verify_comparator,BASELINE_TREE,norm,parse_native,ParseError,mapping,score_document,summarize)
from qualification.mapping_v1.scoring import paired

HERE=Path(__file__).resolve().parent
MAPPING_SOURCE='23e023045b335540d830ce01b75be247552a63f1'
MAPPING_TREE='59f66d0d3d9be145a43efcc9258eb260d3ef2f00'

def protocol():return load_json(HERE/'protocol.json')

def verify_frozen_mappers():
    verify_comparator()
    assert tree('HEAD','qualification/mapping_v1')==MAPPING_TREE,'Accepted mapping v1 changed'
