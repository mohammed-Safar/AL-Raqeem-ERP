import ast
def parse(path):
    entries=[]; cur={}; key=None
    for line in open(path, encoding='utf-8'):
        line=line.rstrip('\n')
        if line.startswith('msgctxt '): cur['ctx']=ast.literal_eval(line[8:]); key='ctx'
        elif line.startswith('msgid '): cur['id']=ast.literal_eval(line[6:]); key='id'
        elif line.startswith('msgstr '): cur['str']=ast.literal_eval(line[7:]); key='str'
        elif line.startswith('"') and key: cur[key]+=ast.literal_eval(line)
        elif line.startswith('#,'): cur['flags']=line
        elif line.startswith('#: '): cur['ref']=cur.get('ref','')+line[3:]+' '
        elif line.strip()=='':
            if 'id' in cur: entries.append(cur)
            cur={}; key=None
    if 'id' in cur: entries.append(cur)
    return [e for e in entries if e.get('id')]
