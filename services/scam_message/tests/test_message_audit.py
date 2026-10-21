from benchmark.audit_messages import summarize


def test_public_jsonl_keeps_unicode_line_separators_inside_message_text(tmp_path):
    import json
    from benchmark.audit_messages import records
    path=tmp_path/'messages.jsonl';message='पहला भाग\u2028दूसरा भाग\u0085अंत'
    path.write_text(json.dumps({'text':message},ensure_ascii=False)+'\n',encoding='utf-8')
    assert records(path)==[{'text':message}]


def test_unknown_scams_are_misses_and_failed_normal_checks_are_not_safe():
    rows=[{'text_sha256':str(i),'is_scam':i<2} for i in range(4)]
    data={'0':{'verdict':'LIKELY_SCAM','status':'SUCCESS'},'1':{'verdict':'UNABLE_TO_ASSESS','status':'SUCCESS'},
          '2':{'verdict':'NO_STRONG_INDICATORS','status':'SUCCESS'},'3':{'error':'Timeout'}}
    result=summarize(rows,data)
    assert result['recall']==.5 and result['precision']==1
    assert result['missed_scams_including_abstentions']==1
    assert result['tn_decided']==1 and result['inconclusive_rate']==.5
    assert result['normal_false_warning_rate']==0 and result['service_errors']==1


def test_selection_is_distinct_balanced_and_reads_hindi_manifest_on_windows(tmp_path):
    import json
    from benchmark.audit_messages import prepare
    source=tmp_path/'source';out=tmp_path/'out';source.mkdir();out.mkdir()
    rows=[{'text':f'Public fixture message class {label} example {i:04d}',
           'is_scam':label,'language':'English','head2_scam_intent':'Fixture'}
          for label in (0,1) for i in range(401)]
    rows.append(rows[0].copy())
    (source/'test.jsonl').write_text('\n'.join(json.dumps(r) for r in rows),encoding='utf-8')
    (source/'comparison-manifest.json').write_text(json.dumps({'rows':[],'note':'हिन्दी'},ensure_ascii=False),encoding='utf-8')
    doc=prepare(source,out)
    assert len(doc['rows'])==len({r['text_sha256'] for r in doc['rows']})==800
    assert sum(r['is_scam'] for r in doc['rows'])==400
