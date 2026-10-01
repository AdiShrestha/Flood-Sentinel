"""Read every nonignored project file; distinguish line scans from semantic proof."""
import ast
import hashlib
import json
import re
from pathlib import Path
import subprocess
from datetime import datetime, timezone


def main():
    root=Path(__file__).resolve().parents[3]
    paths=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=root).decode().split('\0')
    flags=re.compile(r'fabricat|hardcod|synthetic|dummy|fallback|random\.|manual_seed|nan_to_num|fillna|bfill|read_csv|read_parquet|http_status|available_at|frozen|SEALED|ATTESTED',re.I)
    records=[]
    def unique(items):
        out={}
        for key,value in items:
            if key in out: raise ValueError('duplicate JSON key: '+key)
            out[key]=value
        return out
    def reject(value): raise ValueError('nonstandard JSON constant: '+value)
    for rel in sorted(set(paths)-{''}):
        if rel.startswith('project/audit/revalidation/tree_inventory'): continue
        path=root/rel
        if path.is_symlink(): records.append({'path':rel,'kind':'symlink','semantic_authentication':False}); continue
        if not path.is_file(): records.append({'path':rel,'kind':'missing tracked file'}); continue
        data=path.read_bytes(); rec={'path':rel,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}
        if rel.startswith('factory/legacy/') or rel.startswith('docs/'): role='supplied historical factory material'
        elif rel.startswith('project/audit/'): role='audit metadata/forensic evidence; not research observations'
        elif '/tests/' in rel: role='constructed engineering fixtures'
        else: role='active project code/specification'
        rec['role']=role
        try: text=data.decode('utf-8')
        except UnicodeDecodeError: rec['kind']='binary; bytes inventoried only'
        else:
            lines=text.splitlines(); rec.update(kind='text',lines=len(lines),flagged_lines=[i for i,line in enumerate(lines,1) if flags.search(line)])
            try:
                if path.suffix=='.py':
                    tree=ast.parse(text,filename=rel)
                    rec['definitions']=[{'name':node.name,'start':node.lineno,'end':node.end_lineno} for node in ast.walk(tree) if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef))]
                elif path.suffix=='.json': json.loads(text,object_pairs_hook=unique,parse_constant=reject)
                rec['syntax']='checked' if path.suffix in ('.py','.json') else 'not applicable'
            except (SyntaxError,ValueError) as ex: rec['parse_error']=str(ex)
        records.append(rec)
    result={'checked_at':datetime.now(timezone.utc).isoformat(),'scope':'Every Git-tracked/nonignored working file read in full; every text line scanned. This inventory is not a proof of semantics, source authenticity or scientific validity.',
            'files':records,'file_count':len(records),'total_bytes':sum(r.get('bytes',0) for r in records),'text_lines':sum(r.get('lines',0) for r in records)}
    output=Path(__file__).with_name('tree_inventory.json'); output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('file_count','total_bytes','text_lines')}))
    print(json.dumps({'parse_errors':[r['path'] for r in records if 'parse_error' in r],'special_or_missing':[r['path'] for r in records if r.get('kind') in ('symlink','missing tracked file')]}))


if __name__=='__main__': main()
