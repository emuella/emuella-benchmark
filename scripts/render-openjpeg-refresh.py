#!/usr/bin/env python3
"""Render a completed refresh report as a portable, pixel-free HTML document."""
import html
import json
from pathlib import Path
import statistics
import sys

report_path = Path(sys.argv[1])
report = json.loads(report_path.read_text())
comparisons = report['comparisons']
locations = {'94': 'Mansfield', '106': 'Boca Raton', '105': 'Tok'}
rows = []
for item in comparisons:
    case = item['case_id']
    location = locations.get(case.split('_')[0], case)
    product = case.rsplit('-', 1)[1]
    operation = 'Encode' if item['operation'] == 'encode' else 'Decode'
    origin = 'Own output' if item['origin'] == 'own' else item['origin'].title() + ' stream'
    style = 'Style 0' if item['style'] == 0 else 'Bypass'
    cells = [location, product, style, str(item['workers']), operation, origin]
    if 'codecs' in item:
        oj = item['codecs']['openjpeg']; em = item['codecs']['emuella']
        ratio = em['mean_ms']/oj['mean_ms']
        interval = item.get('relative_interval_99')
        interval_text = 'Unbounded' if interval is None else f'{1+interval[0]:.3f}–{1+interval[1]:.3f}'
        cells += [f"{oj['mean_ms']:.3f}", f"{em['mean_ms']:.3f}", f'{ratio:.3f}', interval_text,
                  f"{oj['maximum_process_rss_bytes']/2**20:.1f}", f"{em['maximum_process_rss_bytes']/2**20:.1f}",
                  '/'.join(str(n) for n in oj['stream_bytes']), '/'.join(str(n) for n in em['stream_bytes']), str(item['verdict'])]
    else:
        cells += ['—']*8 + [str(item['verdict'])]
    rows.append('<tr>' + ''.join('<td>'+html.escape(c)+'</td>' for c in cells) + '</tr>')
summary=[]
for style in (0,1):
    for workers in (1,8):
        values=[]
        for operation,origin in (('encode','own'),('decode','openjpeg'),('decode','emuella')):
            selected=[c for c in comparisons if c['style']==style and c['workers']==workers and c['operation']==operation and c['origin']==origin]
            if len(selected)!=9 or any('codecs' not in c for c in selected):
                values.append('Incomplete coverage')
            else:
                ratios=[c['codecs']['emuella']['mean_ms']/c['codecs']['openjpeg']['mean_ms'] for c in selected]
                values.append(f'{statistics.geometric_mean(ratios):.3f}')
        summary.append('<tr><td>'+('Style 0' if style==0 else 'Bypass')+'</td><td>'+str(workers)+'</td>'+''.join('<td>'+v+'</td>' for v in values)+'</tr>')
headers=['Location','Product','Style','Workers','Operation','Stream origin','OpenJPEG ms','Emuella ms','E/O time','99% E/O interval','OpenJPEG peak MiB','Emuella peak MiB','OpenJPEG stream bytes','Emuella stream bytes','Verdict']
page='''<!doctype html><html lang="en-AU"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Emuella–OpenJPEG refreshed comparison</title>
<style>body{font:15px/1.55 system-ui,sans-serif;color:#19252c;background:#f6f8fa;margin:0}main{max-width:1600px;margin:auto;padding:36px}h1{font-size:30px;line-height:1.2}h2{font-size:21px;margin-top:30px}p{max-width:1050px}.panel{background:white;border:1px solid #d9e1e6;border-radius:8px;padding:20px;margin:20px 0}.scroll{overflow:auto}table{border-collapse:collapse;font-variant-numeric:tabular-nums;width:100%;white-space:nowrap}th,td{padding:9px 12px;border-bottom:1px solid #e5eaee;text-align:right}th{background:#eaf0f4;font-size:12px;position:sticky;top:0}td:first-child,th:first-child{text-align:left}tr:nth-child(even){background:#f7fafc}input{font:inherit;padding:9px;border:1px solid #98a9b5;border-radius:4px;min-width:300px}code{overflow-wrap:anywhere}small{color:#526674}@media print{main{padding:8px}.scroll{overflow:visible}table{font-size:8px}input{display:none}}</style><main>
<h1>Emuella–OpenJPEG refreshed comparison</h1><p>Lossless classic JPEG 2000 on nine complete RarePlanes image products. Twenty fresh-process rounds per codec, profile and operation. Matching style, colour transform and CPU budgets; both stream origins decoded independently.</p>
'''
page+=f"<p><strong>Emuella:</strong> <code>{html.escape(report['codec_revision'])}</code><br><strong>OpenJPEG:</strong> {html.escape(report['openjpeg'])}<br><strong>Host:</strong> {html.escape(report['machine']['model'])}<br><strong>Completed:</strong> {html.escape(report['completed_utc'])}</p>"
page+='<p><strong>Coverage:</strong> '+('All planned observations completed and reconstructed exactly.' if report['complete'] else 'Incomplete: failed observations remain recorded; affected comparisons are invalid.')+'</p>'
page+='''<section class="panel"><h2>Descriptive timing summary</h2><p>E/O is Emuella operation time divided by OpenJPEG operation time: below 1 favours Emuella; above 1 favours OpenJPEG. These are equally weighted geometric means of the nine per-image ratios, not a pooled confidence claim. Use the individual intervals and verdicts below to assess uncertainty.</p><div class="scroll"><table><thead><tr><th>Profile</th><th>Workers</th><th>Encode E/O</th><th>Decode OpenJPEG stream E/O</th><th>Decode Emuella stream E/O</th></tr></thead><tbody>'''+''.join(summary)+'''</tbody></table></div></section>
<section class="panel"><h2>All measured comparisons</h2><p>Times are means in milliseconds; lower is better. Peak MiB covers the whole worker process, including setup and verification. Compressed sizes describe each stream, and will match within a common-stream decode contrast. Candidate verdicts refer to Emuella, using the conservative 99% interval and 5% practical threshold.</p><label>Filter rows <input id="filter" placeholder="e.g. Mansfield, Bypass, Decode"></label><p id="count"></p><div class="scroll"><table id="details"><thead><tr>'''+''.join('<th>'+h+'</th>' for h in headers)+'''</tr></thead><tbody>'''+''.join(rows)+'''</tbody></table></div></section>
<h2>Measurement boundary and limits</h2><p>The inner clock starts with loaded interleaved U8/U16_LE bytes or a loaded codestream and includes conversion, codec API work and owned output. Input IO, hashing, profile inspection and complete sample verification are outside that clock. Emuella calls the public facade directly using the global Rayon pool. OpenJPEG calls its installed public API. One-worker contrasts share one CPU; eight-worker contrasts share the same eight-CPU affinity.</p><p>All profiles use raw Part 1, reversible D2, one tile and layer, LRCP, default precincts and 64×64 code blocks. RGB uses reversible colour transform in both codecs; PAN and eight-band MSI use none. Style 0 and bypass are separate measured profiles. No outliers or failed observations are silently discarded.</p><p>This is a fixed nine-product cohort on one host, not the full 48-product coverage study, a general codec ranking or a measurement of HTJ2K, lossy coding, ROI, persistent services or concurrent requests. Requested worker counts do not prove participation. Codec allocation limits and whole-process RSS are distinct.</p>
<p><small>RarePlanes Dataset, June 2020. J. Shermeyer, T. Hossler, A. Van Etten, D. Hogan, R. Lewis and D. Kim; In-Q-Tel – CosmiQ Works and AI.Reverie. CC BY-SA 4.0. Factual measurements only; no image payload. Full numerical provenance accompanies this report in report.json.</small></p>
</main><script>const input=document.querySelector('#filter'),rows=[...document.querySelectorAll('#details tbody tr')];function filter(){let words=input.value.toLowerCase().split(/\\s+/).filter(Boolean),n=0;for(const row of rows){const ok=words.every(w=>row.textContent.toLowerCase().includes(w));row.hidden=!ok;if(ok)n++}document.querySelector('#count').textContent=`${n} of ${rows.length} comparisons shown`}input.addEventListener('input',filter);filter();</script></html>'''
report_path.with_suffix('.html').write_text(page)
print(report_path.with_suffix('.html'))
