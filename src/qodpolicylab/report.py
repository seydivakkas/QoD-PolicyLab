"""Safe, static, fully local HTML summary, without JavaScript or CDN assets."""
from __future__ import annotations
from html import escape
from pathlib import Path
import json


def render_report(run_folder, output=None):
    folder=Path(run_folder)
    metrics=json.loads((folder/'metrics.json').read_text(encoding='utf-8'))
    title='QoD-PolicyLab — simulated network only'
    if 'summary' in metrics:
        rows=[]
        for name,score in metrics['summary'].items():
            rows.append((name,score['average_miss_rate'],score['average_service_cost_units']))
        headers=['Policy','Mean deadline miss rate','Mean service cost (synthetic units)']
    else:
        rows=[(metrics['policy'],metrics['deadline_miss_rate'],metrics['service_cost_units'])]
        headers=['Policy','Deadline miss rate','Service cost (synthetic units)']
    th=''.join(f'<th scope="col">{escape(h)}</th>' for h in headers)
    trs=''.join('<tr>'+''.join(f'<td>{escape(str(x))}</td>' for x in row)+'</tr>' for row in rows)
    html=('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
          f'<title>{title}</title><style>body{{font:16px system-ui;max-width:850px;margin:35px auto;padding:20px;color:#17212b}}'
          'table{border-collapse:collapse;width:100%}td,th{border:1px solid #ccd1d5;padding:10px;text-align:left}th{background:#eaf0f4}'
          '</style></head><body><h1>QoD-PolicyLab</h1><p><strong>SIMULATED ONLY</strong>: hypothetical response and costs, not a measured 5G SLA.</p>'
          f'<table><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table>'
          '<p>Counterfactual benefit is conditioned on the model and immutable exogenous traces; review per-seed data before any interpretation.</p></body></html>')
    path=Path(output) if output else folder/'report.html'
    path.write_text(html+'\n',encoding='utf-8')
    return path