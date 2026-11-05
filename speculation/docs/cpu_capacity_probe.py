import hashlib,json,platform,sys,time,tracemalloc
from pathlib import Path
from recallspec.core import Config,RetrievalIndex
tracemalloc.start()
i=RetrievalIndex(Config())
start=time.perf_counter()
for request in range(1000):
 tokens=[request*1000+n for n in range(51)]
 i.tick(); i.commit(str(request),tokens,12);i.finish(str(request))
 assert len(i.entries)<=50000
current,peak=tracemalloc.get_traced_memory()
result={'kind':'CPU-only capacity stress; not an inference benchmark','platform':platform.platform(),'python':sys.version,'requests':1000,'keys':len(i.entries),'live_cursors':len(i.cursors),'pending':len(i.pending),'stats':dict(i.stats),'tracemalloc_current_bytes':current,'tracemalloc_peak_bytes':peak,'wall_seconds_including_tracemalloc':time.perf_counter()-start,'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
(Path(__file__).resolve().parents[1]/'results/cpu-capacity.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
