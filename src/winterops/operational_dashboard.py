"""Self-contained, offline dashboard with compact, allowlisted aggregate tables."""
import json
from pathlib import Path

from winterops.weather import canonical

TABLES = ('weekly', 'daily', 'hourly', 'calendar', 'cells', 'weather_hourly')


def pack(bundle):
    output = {k: v for k, v in bundle.items() if k not in TABLES}
    output['table_encoding'] = 'columns-and-rows-v1'
    output['tables'] = {}
    for name in TABLES:
        rows = bundle[name]
        fields = list(rows[0]) if rows else []
        output['tables'][name] = dict(columns=fields, rows=[[r[f] for f in fields] for r in rows])
    return output


def unpack(packed):
    result = {k: v for k, v in packed.items() if k not in ('table_encoding', 'tables')}
    for name, table in packed['tables'].items():
        result[name] = [dict(zip(table['columns'], row)) for row in table['rows']]
    return result


def render_dashboard(bundle):
    template = (Path(__file__).parent / 'templates' / 'operations.html').read_text(encoding='utf-8')
    # '<' escaping prevents data from terminating the inert JSON script element.
    data = canonical(pack(bundle)).decode().replace('<', '\\u003c').replace('&', '\\u0026')
    return template.replace('__WINTEROPS_DATA__', data)
