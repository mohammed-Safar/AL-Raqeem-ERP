import sys
def check(src):
    st=[]; i=0; n=len(src); line=1; mode=['code']
    pairs={')':'(',']':'[','}':'{'}
    while i<n:
        c=src[i]; m=mode[-1]
        if c=='\n': line+=1
        if m=='code':
            if src.startswith('//',i): j=src.find('\n',i); i=n if j<0 else j; continue
            if src.startswith('/*',i): j=src.find('*/',i); line+=src[i:j].count('\n'); i=j+2; continue
            if c in '"\'': mode.append(c)
            elif c=='`': mode.append('`')
            elif c in '([{': st.append((c,line))
            elif c in ')]}':
                if c=='}' and st and st[-1][0]=='${': st.pop(); mode.pop(); i+=1; continue
                if not st or st[-1][0]!=pairs[c]: return f'unbalanced {c} at line {line} (open {st[-1] if st else None})'
                st.pop()
        elif m in '"\'':
            if c=='\\': i+=2; continue
            if c==m: mode.pop()
            elif c=='\n': return f'newline in string at line {line}'
        elif m=='`':
            if c=='\\': i+=2; continue
            if c=='`': mode.pop()
            elif src.startswith('${',i): st.append(('${',line)); mode.append('code'); i+=2; continue
        i+=1
    return 'ok' if not st and mode==['code'] else f'unclosed {st[-3:]} mode {mode}'
for f in sys.argv[1:]: print(check(open(f).read()), f)
