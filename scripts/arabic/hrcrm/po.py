import re, ast
def parse(path):
    """list of dicts: id, ctx, str, refs (simple PO parser, handles multi-line strings)"""
    out=[]; cur={}; key=None; refs=[]
    def flush():
        nonlocal cur, refs
        if 'msgid' in cur and cur['msgid']:
            out.append({'id':cur['msgid'],'ctx':cur.get('msgctxt',''),'str':cur.get('msgstr',''),'refs':refs})
        cur={}; refs=[]
    for line in open(path,encoding='utf-8'):
        line=line.rstrip('\n')
        if not line.strip(): flush(); key=None; continue
        if line.startswith('#:'): refs.append(line[2:].strip()); continue
        if line.startswith('#'): continue
        m=re.match(r'(msgctxt|msgid|msgstr)\s+(".*")$',line)
        if m: key=m.group(1); cur[key]=ast.literal_eval(m.group(2)); continue
        if line.startswith('"') and key: cur[key]+=ast.literal_eval(line)
    flush(); return out
