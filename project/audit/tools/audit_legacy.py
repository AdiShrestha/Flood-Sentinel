"""Read-only legacy inventory. Never import or execute legacy result producers.

This inspects bytes and table structure; it cannot authenticate a provider.
"""
import argparse
import ast
import collections
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import re
import zipfile

import pyarrow.parquet as pq

TEXT = {'.py', '.md', '.json', '.jsonl', '.yaml', '.yml', '.txt', '.bib',
        '.tex', '.csv', '.sh', '.svg', '.gitignore'}
PATTERN = re.compile(r'fallback|synthetic|mock|placeholder|fabricat|nwm_sim|nwm_cms|'
                     r'current_swe|melt_factor|interpolate\(|bfill\(|crossing_timestamp|'
                     r'auc_g = 0\.5|camels = True|http_status.*200|causally_valid.*True|'
                     r't_target_dt|median_cal.*get\(|max_samples|sample\(n=min|'
                     r'epochs|wilcoxon|SUPPORTED|Under Peer Review', re.I)


def inspect_bytes(data, suffix):
    result = {'sha256': hashlib.sha256(data).hexdigest(), 'size_bytes': len(data)}
    if suffix == '.parquet':
        try:
            table = pq.read_table(io.BytesIO(data))
            result['table'] = {'rows': table.num_rows, 'columns': table.column_names,
                               'schema': str(table.schema),
                               'null_counts': {n: table[n].null_count for n in table.column_names}}
            # Consume all columns, preserving missingness in the diagnostic.
            numerical = {}
            for n in table.column_names:
                typ = str(table[n].type)
                if typ.startswith(('double', 'float', 'int', 'uint')):
                    vals = table[n].to_pylist()
                    finite = [x for x in vals if x is not None and math.isfinite(x)]
                    numerical[n] = {'nonfinite': sum(x is not None and not math.isfinite(x) for x in vals),
                                    'min': min(finite) if finite else None,
                                    'max': max(finite) if finite else None,
                                    'distinct': len(set(finite))}
            result['table']['numerical'] = numerical
        except Exception as e:
            result['parse_error'] = type(e).__name__ + ': ' + str(e)
    elif suffix in TEXT or suffix == '':
        try:
            text = data.decode('utf-8')
            result['text_lines'] = len(text.splitlines())
            result['flagged_lines'] = [{'line': i, 'text': line[:450]}
                                       for i, line in enumerate(text.splitlines(), 1) if PATTERN.search(line)]
            if suffix == '.py':
                tree = ast.parse(text)
                result['definitions'] = [{'name': n.name, 'line': n.lineno, 'end_line': n.end_lineno}
                                        for n in ast.walk(tree)
                                        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
            elif suffix == '.json':
                pairs = []
                def hook(items):
                    names = [k for k, v in items]
                    pairs.extend(k for k, c in collections.Counter(names).items() if c > 1)
                    return dict(items)
                value = json.loads(text, object_pairs_hook=hook)
                result['duplicate_json_keys'] = sorted(set(pairs))
                result['json_top_keys'] = list(value) if isinstance(value, dict) else None
                result['json_type'] = type(value).__name__
            elif suffix == '.jsonl':
                for line in text.splitlines():
                    if line.strip(): json.loads(line)
        except (UnicodeDecodeError, SyntaxError, ValueError) as e:
            result['parse_error'] = type(e).__name__ + ': ' + str(e)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--legacy', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    root = args.legacy.resolve()
    args.out.mkdir(parents=True, exist_ok=True)
    rows, archives, cache, omitted = [], [], {}, []
    for path in sorted(root.rglob('*')):
        rel = path.relative_to(root)
        if '.git' in rel.parts: continue
        if not path.is_file(): continue
        if path.is_symlink():
            omitted.append({'path': str(rel), 'reason': 'symlink; not followed'})
            continue
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if digest not in cache:
            cache[digest] = inspect_bytes(data, path.suffix)
        result = cache[digest]
        category = 'primary_source' if rel.parts[0] == 'source' else 'historical_artifact'
        if rel.parts[0] in ('DROP_HERE', 'TAKE_THIS'): category = 'handoff_copy'
        if '__pycache__' in rel.parts or '.pytest_cache' in rel.parts or path.name == '.DS_Store': category = 'cache_or_os_metadata'
        rows.append({'path': str(rel), 'category': category, 'sha256': digest,
                     'size_bytes': len(data), 'inspection': result})
        if zipfile.is_zipfile(io.BytesIO(data)):
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                for member in z.infolist():
                    if member.is_dir(): continue
                    raw = z.read(member)
                    md = hashlib.sha256(raw).hexdigest()
                    if md not in cache: cache[md] = inspect_bytes(raw, Path(member.filename).suffix)
                    archives.append({'archive': str(rel), 'member': member.filename,
                                     'sha256': md, 'size_bytes': len(raw),
                                     'unsafe_member_name': member.filename.startswith('/') or '..' in Path(member.filename).parts,
                                     'inspection': cache[md]})
    payload = {'scope': 'Every regular legacy file outside .git; archives read without extraction. '
                        'Text/AST/JSON parsing and complete unique Parquet reads; no provider authentication.',
               'file_count': len(rows), 'archive_member_count': len(archives),
               'unique_contents_including_archives': len(cache), 'omitted': omitted,
               'categories': dict(collections.Counter(r['category'] for r in rows)),
               'files': rows, 'archive_members': archives}
    # Deduplicate details to keep the portable evidence reasonably small.
    for row in rows + archives: row.pop('inspection')
    payload['content_inspections'] = cache
    (args.out / 'legacy_inventory.json').write_text(json.dumps(payload, indent=2, allow_nan=False) + '\n')
    with (args.out / 'legacy_inventory.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['path', 'category', 'sha256', 'size_bytes'])
        writer.writeheader(); writer.writerows(rows)
    print(json.dumps({k: payload[k] for k in ('file_count', 'archive_member_count', 'unique_contents_including_archives', 'categories', 'omitted')}, indent=2))


if __name__ == '__main__':
    main()
