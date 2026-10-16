"""One isolated workflow/package check; mocked external stages, no real approval."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pipeline_io import digest, now

DRIVER = r'''
import copy, json, os, sys
from pathlib import Path
from content.drafts import load_inputs, render_script, source_footer, source_notes
from pipeline_io import ROOT, emit, load, records, save, stage
from review.check_content import assess
name, path = sys.argv[1:]
directory = Path(path).resolve()
run = load(directory/'run.json')
run.update(mode='example', scope='offline_workflow_fixture', as_of_date='2026-10-08', note='Isolated fictional fixture with stubbed external collection/model stages. No live requests or real student approval.')
save(directory/'run.json',run)
with stage(name,directory) as receipt:
    receipt['tools']=['Offline fixture stub; no external requests']
    if os.environ.get('WORKFLOW_TEST_FAIL_STAGE')==name:
        raise RuntimeError('Deliberately simulated offline component failure')
    if name.startswith('fetch_'):
        kind={'fetch_feeds':'feed','fetch_youtube':'youtube','fetch_podcasts':'podcast'}[name]
        with (ROOT/'examples/items.jsonl').open() as stream: rows=[x for x in records(stream) if x['kind']==kind]
    elif name=='extract_content':
        rows=list(records(sys.stdin))
    elif name=='select_items':
        rows=[dict(item_id=x['item_id'],version_id=x['version_id'],decision='accept',reason='Fictional offline interface evidence, not a real editorial judgment.',piece_ids=['01','02','03']) for x in records(sys.stdin)]
    elif name=='create_briefs':
        with (ROOT/'examples/briefs.jsonl').open() as stream: original=next(records(stream))
        rows=[]
        for piece in ('01','02','03'):
            b=copy.deepcopy(original); b['piece_id']=piece; b['title']+=' '+piece; b['argument']+=' '+piece
            for c in b['claims']: c['claim_id']=piece+'-c'+c['claim_id'].split('-c')[1]
            rows.append(b)
    elif name in ('write_articles','write_video_scripts'):
        briefs,evidence=load_inputs(directory); rows=[]
        kind='articles' if name=='write_articles' else 'video_scripts'
        (directory/kind).mkdir(exist_ok=True)
        for b in briefs:
            piece=b['piece_id']; ids=[c['claim_id'] for c in b['claims']]
            notes=source_notes(b,evidence,run['as_of_date']); save(directory/'source_notes'/(piece+'.json'),notes)
            if kind=='articles':
                prose='This is fictional prose for an offline interface check. '*75
                prose+='[^1]<!-- claim:'+ids[0]+' --> [^2]<!-- claim:'+ids[1]+' -->'
                body='# '+b['title']+chr(10)*2+prose
            else:
                scenes=[{'narration':'Fictional narration for this offline check only. '*18,'visual':'Illustrative offline test card; no generated assets.','claim_ids':[ids[k]] if k<2 else []} for k in range(4)]
                value={'piece_id':piece,'scenes':scenes}; save(directory/'video_scenes'/(piece+'.json'),value)
                body=render_script(value,b)
            file=directory/kind/(piece+'.md'); file.write_text(body+chr(10)*2+source_footer(notes))
            rows.append({'piece_id':piece,'path':str(file.relative_to(ROOT)),'claim_ids':ids})
    elif name=='check_content':
        result=assess(directory)
        if os.environ.get('WORKFLOW_TEST_REVIEW_FAIL'):
            result['passed']=False; result['issues'].append({'piece_id':None,'artifact':'fixture','severity':'error','explanation':'Deliberately simulated completed assessment with blocking issues.'})
        rows=[result]
    for row in rows: emit(row)
    receipt['output_count']=len(rows)
'''


def main():
    with tempfile.TemporaryDirectory(prefix='ps04-workflow-fixture-') as temporary:
        project = Path(temporary)
        for name in ('pipeline_io.py','run.sh'):
            shutil.copyfile(ROOT/name, project/name)
        for folder in ('collectors','processing','data','editorial','content','review','publishing','reporting','workflows'):
            (project/folder).mkdir()
            for path in (ROOT/folder).glob('*'):
                if path.suffix in ('.py','.sh'): shutil.copyfile(path,project/folder/path.name)
        for folder in ('config','prompts','examples'): shutil.copytree(ROOT/folder,project/folder)
        (project/'fixture_stage.py').write_text(DRIVER)
        replacements = {
            'collectors/fetch_feeds.sh':'fetch_feeds','collectors/fetch_youtube.sh':'fetch_youtube','collectors/fetch_podcasts.sh':'fetch_podcasts',
            'processing/extract_content.sh':'extract_content','editorial/select_items.sh':'select_items','editorial/create_briefs.sh':'create_briefs',
            'content/write_articles.sh':'write_articles','content/write_video_scripts.sh':'write_video_scripts','review/check_content.sh':'check_content'}
        for filename, stage_name in replacements.items():
            (project/filename).write_text('#!/usr/bin/env bash\nexec "$PIPELINE_PYTHON" fixture_stage.py '+stage_name+' "$@"\n')
        env=dict(os.environ,PIPELINE_PYTHON=sys.executable)
        def call(args, code=0, extra=None):
            result=subprocess.run(['bash',*args],cwd=project,env=dict(env,**(extra or {})),text=True,capture_output=True,timeout=120)
            assert result.returncode==code,(args,result.returncode,result.stdout,result.stderr)
            return json.loads(result.stdout) if result.stdout.strip() else None
        first=call(['run.sh']); assert first['status']=='awaiting_review' and not first['complete_live_run'],first
        run=project/'runs'/first['run_id']
        assert first['counts']['articles']==first['counts']['video_scripts']==3
        frozen={str(p.relative_to(run)):p.read_bytes() for p in run.rglob('*') if p.is_file() and (p.suffix=='.md' or '/config/' in str(p) or '/prompts/' in str(p))}
        blocked=call(['run.sh','--package',str(run.relative_to(project))],code=1)
        assert blocked['status']=='awaiting_review' and not (run/'package').exists()
        assert all((run/name).read_bytes()==data for name,data in frozen.items())
        review=json.loads((run/'review.json').read_text())
        (run/'approval.json').write_text(json.dumps({'review_id':review['review_id'],'decision':'approve','reviewer':'Fictional offline fixture reviewer','reviewed_at':now(),'notes':'Simulated approval of fictional example material in an isolated test only; not real student approval.'}))
        ready=call(['run.sh','--package',str(run.relative_to(project))]); assert ready['status']=='ready_for_production'
        package=run/'package'; links=json.loads((package/'publication_links.json').read_text())
        links[0]['substack_url']='https://fixture.example/article/01'; links[0]['fixture_note']='Not a real publication URL.'
        (package/'publication_links.json').write_text(json.dumps(links))
        call(['run.sh','--package',str(run.relative_to(project))])
        assert json.loads((package/'publication_links.json').read_text())==links
        assert len(json.loads((package/'manifest.json').read_text())['assets'])==9
        assert list(run.glob('package-backup-*'))
        asset=package/'articles/01.md'; asset.write_text(asset.read_text().replace('This is fictional prose','This is tampered fictional prose',1))
        manifest=json.loads((package/'manifest.json').read_text())
        entry=next(a for a in manifest['assets'] if a['kind']=='articles' and a['piece_id']=='01')
        entry['content_digest']=digest(asset.read_text()); (package/'manifest.json').write_text(json.dumps(manifest))
        tampered=call(['reporting/summarize_run.sh',str(run.relative_to(project))])
        assert tampered['status']=='awaiting_review' and tampered['package_validation_error']
        call(['run.sh','--package',str(run.relative_to(project))])
        before={str(p.relative_to(package)):hashlib.sha256(p.read_bytes()).hexdigest() for p in package.rglob('*') if p.is_file()}
        article=run/'articles/01.md'; article.write_text(article.read_text().replace('This is fictional prose','This is changed fictional prose',1))
        call(['publishing/prepare_package.sh',str(run.relative_to(project))],code=1)
        assert before=={str(p.relative_to(package)):hashlib.sha256(p.read_bytes()).hexdigest() for p in package.rglob('*') if p.is_file()}
        stale=call(['run.sh','--package',str(run.relative_to(project))],code=1); assert stale['status']=='awaiting_review'
        failure=call(['run.sh'],code=1,extra={'WORKFLOW_TEST_FAIL_STAGE':'select_items'})
        assert failure['status']=='failed' and failure['counts']['briefs'] is None
        rejected=call(['run.sh'],code=1,extra={'WORKFLOW_TEST_REVIEW_FAIL':'1'})
        assert rejected['status']=='failed' and rejected['review_status']=='stale_or_failed'
        replay=call(['run.sh']); assert replay['counts']['unchanged']==3 and replay['counts']['new']==0
    print('Workflow/package checks passed: real Bash coordination and SQLite, fictional external stages, summary-on-failure, completed-but-failed assessment, missing/stale approval, positive fixture packaging, preserved links, backups, unchanged drafts, and duplicate replay. No paid calls or real approval.')


if __name__=='__main__': main()
