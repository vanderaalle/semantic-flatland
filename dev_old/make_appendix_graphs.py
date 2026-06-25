import math, os, re, sys
from collections import Counter
sys.path.insert(0, '/home/claude')
import graphviz

# inline lemmatizer
KEEP_AS_IS = {'disembodied','deceased','dead','matter','blessed','cursed','learned',
    'aged','naked','sacred','beloved','wicked','noted','related','matter'}
IRREGULAR = {'ghosts':'ghost','corpses':'corpse','gyrations':'gyration',
    'demons':'demon','bodies':'body','brothers':'brother','stories':'story',
    'tales':'tale','travellers':'traveller','wayfarers':'wayfarer'}
def lemmatize(w):
    w=w.lower()
    if w in KEEP_AS_IS: return w
    if w in IRREGULAR: return IRREGULAR[w]
    for s,r in [('tion',''),('sion',''),('ness',''),('ment',''),('ings',''),
                ('ing',''),('edly',''),('ies','y'),('ied','y'),('ed',''),
                ('es',''),('er',''),('ly',''),('s','')]:
        if w.endswith(s) and len(w)-len(s)>2: return w[:-len(s)]+r
    return w

from isotopy import LEMMA_MAP, NUCLEAR_BASE, W1828
LEMMAS = sorted(LEMMA_MAP.keys())
LEMMA_SET = set(LEMMAS)
NUCLEAR = NUCLEAR_BASE | LEMMA_SET
N = len(LEMMAS)

def extract_words(text, lemma, nuclear):
    return [lw for w in re.findall(r'[a-z]+', text.lower())
            for lw in [lemmatize(w)]
            if lw not in nuclear and len(lw)>2 and lw!=lemma]

lemma_words = {}
for lemma in LEMMAS:
    defn = W1828.get(lemma,'')
    lemma_words[lemma] = extract_words(defn, lemma, NUCLEAR) if defn else []

word_count = Counter(w for ws in lemma_words.values() for w in set(ws))
IDF = {w: math.log(N/c) for w,c in word_count.items() if c <= N*0.45}

OUT_DIR = '/home/claude/appendix_graphs'
os.makedirs(OUT_DIR, exist_ok=True)

for i, lemma in enumerate(LEMMAS):
    g = graphviz.Digraph(name=lemma, engine='dot',
        graph_attr={'rankdir':'LR','bgcolor':'white','margin':'0.1',
                    'nodesep':'0.3','ranksep':'0.55','fontname':'Helvetica'},
        node_attr={'fontname':'Helvetica','fontsize':'9','margin':'0.08,0.04'},
        edge_attr={'fontname':'Helvetica','fontsize':'7.5','arrowsize':'0.5'})
    g.node(lemma, label=lemma.upper(), shape='box', style='filled,rounded',
           fillcolor='#1a1a1a', fontcolor='white', fontsize='10',
           fontweight='bold', penwidth='0')
    l1 = sorted([(w,IDF[w]) for w in lemma_words.get(lemma,[]) if w in IDF],
                key=lambda x:x[1], reverse=True)[:8]
    for w, idf_w in l1:
        g.node(f'l1_{w}', label=w, shape='box', style='filled,rounded',
               fillcolor='#e8e8e8', color='#999999', penwidth='0.5')
        g.edge(lemma, f'l1_{w}', label=f'{idf_w:.2f}', color='#444444', fontcolor='#666666')
    g.render(os.path.join(OUT_DIR, lemma), format='png', cleanup=True)
    print(f'  [{i+1:2d}/{N}] {lemma}')
print('Done.')
