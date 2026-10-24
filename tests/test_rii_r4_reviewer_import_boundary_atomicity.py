"""Independent R-II round-4 check of by-ID guards after import planning.

Use a real second connection to install a redaction or reservation. A refused
import must roll back even its earlier, unrelated edge write. Fresh-ID controls
must remain admissible. All fixtures use public store/Memory operations.
"""
import pytest
from veracium import Memory,MemoryConfig
from veracium.schema import Episode,Edge,Provenance,EvidenceAuthor,ConsolidationOutputDraft,ConsolidationState as CS

A='independent-a';B='independent-b';HELD='independent-held'

def memory(path):
    return Memory(llm=lambda prompt,**kw:'Local fixture.',config=MemoryConfig(db_path=str(path),require_source_id=False,scope_groups={}))

def episode(eid,uid=A):
    return Episode(id=eid,user_id=uid,date='2026-01-02',summary='A local fixture.',
                   provenance=Provenance(author_of_evidence=EvidenceAuthor.USER,evidence_ref='local-event'))

def state(s):
    return tuple(s._conn.iterdump())

def install_guard(s,hazard):
    s.add_episode(episode(HELD))
    if hazard=='redaction':
        s.redact(A,episode_id=HELD,reason='subject_request')
        s.delete_episode(HELD)
        assert HELD in s.redacted_targets(A,'episode')
    else:
        s.add_episode(episode('independent-second-input'))
        op=s.create_or_takeover_consolidation(A,[HELD,'independent-second-input'],'review-writer',60)
        assert s.transition_consolidation_if_current(op.operation_id,op.fence,'review-writer',CS.GENERATING)
        assert s.write_consolidation_output_if_current(op.operation_id,op.fence,'review-writer',ConsolidationOutputDraft(
            summary='Two inputs.',date_start='2026-01-02',date_end='2026-01-02'))
        assert s.transition_consolidation_if_current(op.operation_id,op.fence,'review-writer',CS.OUTPUTS_DURABLE)
        assert s.delete_claimed_inputs_if_current(op.operation_id,op.fence)
        assert HELD in s._reserved_ids(A)
    assert not s._conn.execute('SELECT 1 FROM episodes WHERE id=?',(HELD,)).fetchone()

@pytest.mark.parametrize('hazard',['redaction','reservation'])
@pytest.mark.parametrize('restore',[False,True],ids=['import','restore'])
@pytest.mark.parametrize('timing',['before_preflight','before_commit'])
@pytest.mark.parametrize('conflicting',[True,False],ids=['held-id','fresh-id'])
def test_import_checks_durable_id_state_and_rolls_back_prefix(tmp_path,monkeypatch,hazard,restore,timing,conflicting):
    src=memory(tmp_path/'source.db');dst=memory(tmp_path/'destination.db');writer=memory(tmp_path/'destination.db')
    target=HELD if conflicting else 'independent-fresh'
    path=tmp_path/'arrival.jsonl';before=[];commits=[]
    try:
        src.store.add_edge(Edge(id='independent-prefix',user_id=B,subject='user',relation='likes',object='tea',
                        provenance=Provenance(author_of_evidence=EvidenceAuthor.USER,evidence_ref='local-edge')))
        src.store.add_episode(episode(target,B));src.export_memory(B,str(path))
        dst.store.add_episode(episode('independent-sentinel',B))
        assert dst.store.set_wiki(B,'B cache',dst.store.store_version(B))
        if timing=='before_preflight':
            install_guard(writer.store,hazard);before.append(state(dst.store))
        real=dst.store.commit_outcome_import_plan
        def commit(*args,**kw):
            if timing=='before_commit' and not commits:
                install_guard(writer.store,hazard);before.append(state(dst.store))
            commits.append(True)
            return real(*args,**kw)
        monkeypatch.setattr(dst.store,'commit_outcome_import_plan',commit)
        def run():
            return dst.import_memory(str(path),restore=True) if restore else dst.import_memory(str(path),user_id=B)
        if conflicting:
            with pytest.raises(ValueError,match='under another owner|reserved by an in-flight consolidation'):run()
            assert commits and len(before)==1
            assert state(dst.store)==before[0], 'a refused import changed durable rows'
            assert not dst.store._conn.execute("SELECT 1 FROM edges WHERE id='independent-prefix'").fetchone()
        else:
            run();assert commits
            assert {e.id for e in dst.store.episodes(B)}=={'independent-sentinel',target}
            assert dst.store._conn.execute("SELECT 1 FROM edges WHERE id='independent-prefix'").fetchone()
    finally:
        src.close();dst.close();writer.close()
