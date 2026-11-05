from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parents[1]
final=root/'results/final'
stages=['strict','performance','diagnostics','fallback','prefix','default-runner','7b','strict128']
manifest=json.loads((root/'patches/manifest.json').read_text())
fingerprint=json.loads((final/'source-fingerprint.json').read_text())
source_differences=[]
for name,digest in fingerprint.items():
 p=root/name
 assert p.exists(),name
 if hashlib.sha256(p.read_bytes()).hexdigest()!=digest:source_differences.append(name)
assert source_differences==['tools/analyze.py'],source_differences
runs=records=requests=0
for stage in stages:
 assert (final/(stage+'.done')).exists(),stage
 folder=final/stage
 for f in sorted(folder.glob('*-s*.json')):
  d=json.loads(f.read_text()); assert d.get('completed'),f
  args=d['args'];expected_records=len(args['kinds'].split(','))*len(args['batches'].split(','))*args['rounds']
  assert len(d['records'])==expected_records,(f,len(d['records']),expected_records)
  for name,digest in d['source_hashes'].items():
   if name.startswith('src/'):
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,(f,name)
  desired='patched_sha256' if args['mode'] in ('gated','ungated') or args.get('trace') else 'original_sha256'
  assert d['source_hashes']['vllm/v1/worker/gpu_model_runner.py']==manifest[desired],f
  for r in d['records']:
   assert len(r['outputs'])==r['batch'],f
   for o in r['outputs']:
    assert len(o['token_ids'])==args['tokens'],(f,o['request_id'],len(o['token_ids']))
    requests+=1
   records+=1
  runs+=1
strict=json.loads((final/'strict/summary.json').read_text())
assert len(strict['comparisons'])==3
for name,item in strict['comparisons'].items():
 assert item['total']==81 and item['identical']==81,(name,item)
strict128=json.loads((final/'strict128/summary.json').read_text())
for name,item in strict128['comparisons'].items():
 assert item['total']==81 and item['identical']==81,(name,item)
traces=[]
for folder in (final/'strict',final/'strict128',final/'diagnostics'):
 for trace in sorted(folder.glob('*-trace')):
  events=[]
  for f in trace.glob('*.jsonl'):events.extend(json.loads(s) for s in f.read_text().splitlines())
  assert events,trace
  for e in events:
   assert e.get('keys',0)<=50000
   for feedback in e.get('feedback',[]):assert 0<=feedback['accepted']<=feedback['scheduled']
  last=[e for e in events if e['event']=='schedule'][-1]
  assert last['live_cursors']==0 and last['pending']==0,(trace,last)
  traces.append({'trace':str(trace.relative_to(root)),'events':len(events),'final_live_cursors':0,'final_pending':0,'max_keys':max(e.get('keys',0) for e in events)})
audit={'completed_stages':stages,'runs':runs,'records':records,'requests':requests,'runtime_source_hashes_match':True,'strict_full_token_pairs':{name:{k:v for k,v in item.items() if k!='differences'} for name,item in strict['comparisons'].items()},'analysis_only_revision':{'file':'tools/analyze.py','measurement_sha256':fingerprint['tools/analyze.py'],'corrected_sha256':hashlib.sha256((root/'tools/analyze.py').read_bytes()).hexdigest(),'reason':'Resolve external IDs to actual worker IDs using a unique mapping from schedule events; two regression tests. Runtime, workload and original measurements unchanged.'},'strict128_full_token_pairs':{name:{k:v for k,v in item.items() if k!='differences'} for name,item in strict128['comparisons'].items()},'trace_checks':traces}
(final/'release-verification.json').write_text(json.dumps(audit,indent=2)+'\n')
print(json.dumps(audit,indent=2))
