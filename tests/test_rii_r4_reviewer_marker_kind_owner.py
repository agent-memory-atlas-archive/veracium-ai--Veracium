"""The disclosed MARKER-kind seam, using the shipped historical-store fixture.

Only the fixture construction is reused; the cross-owner arrival and oracle
are independent. REVIEW_MUTATE_COVERAGE enables a deliberate reader-key mutant.
"""
from pathlib import Path
import importlib.util,json,os
import pytest
import veracium
from veracium import Memory,MemoryConfig,portability
from veracium.schema import Episode,EvidenceAuthor,Provenance
from veracium import redaction
from veracium.store import sqlite

TREE=Path(veracium.__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('review_kind_fixture',TREE/'tests/test_0041_round10_notices.py')
fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)

def mem(p):
    return Memory(llm=lambda prompt,**kw:'local',config=MemoryConfig(db_path=str(p),require_source_id=False,scope_groups={}))

def write(p,rows):
    p.write_text(''.join(json.dumps(r)+'\n' for r in rows));return p

@pytest.mark.parametrize('notice',['none','same-owner','other-owner'])
@pytest.mark.parametrize('restore',[False,True],ids=['import','restore'])
def test_marker_kind_coverage_is_owned_by_the_destination(tmp_path,monkeypatch,notice,restore):
    if os.environ.get('REVIEW_MUTATE_COVERAGE')=='1':
        original=sqlite.SqliteStore._attested_fields
        def by_id(self,user_id,kind,target_id,*,coverage=False):
            return original(self,sqlite._ANY_OWNER,kind,target_id,coverage=coverage)
        monkeypatch.setattr(sqlite.SqliteStore,'_attested_fields',by_id)
    eid,exported=fixture._redacted_prose_kind_export(tmp_path)
    rows=[json.loads(x) for x in exported.read_text().splitlines()]
    notice_rows=[r for r in rows if r.get('record')=='redaction']
    treated=next(r for r in rows if r.get('record')=='episode' and r['id']==eid)
    assert len(notice_rows)==1 and 'kind' in notice_rows[0]['fields']
    owner=fixture.U if notice=='same-owner' else 'review-other-kind-owner'
    src=mem(tmp_path/'arrival-source.db');dst=mem(tmp_path/'arrival-destination.db')
    try:
        if notice!='none':
            head=[r for r in rows if r.get('record') not in ('episode','edge','redaction')]
            result=portability.import_memory(dst.store,write(tmp_path/'notice.jsonl',head+notice_rows),restore=True)
            assert result['notices_standing']==1
        src.store.add_episode(Episode(id=eid,user_id=owner,date='2026-01-02',summary='Fresh arrival.',
                              provenance=Provenance(author_of_evidence=EvidenceAuthor.USER,evidence_ref='review-event')))
        path=tmp_path/'arrival.jsonl';src.export_memory(owner,str(path))
        arrival=[json.loads(x) for x in path.read_text().splitlines()];changed=0
        for r in arrival:
            if r.get('record')=='episode' and r['id']==eid:
                r.clear();r.update(treated);r['user_id']=owner;changed+=1
        assert changed==1;write(path,arrival)
        def run():
            return dst.import_memory(str(path),restore=True) if restore else dst.import_memory(str(path),user_id=owner)
        if notice=='same-owner':
            run()
            assert dst.store._conn.execute('SELECT 1 FROM episodes WHERE id=? AND user_id=?',(eid,owner)).fetchone()
        else:
            with pytest.raises(ValueError,match='not a recognised operational kind'):run()
            assert not dst.store._conn.execute('SELECT 1 FROM episodes WHERE id=?',(eid,)).fetchone()
    finally:src.close();dst.close()
