import sys, os, re, time, json, urllib.request
from collections import Counter, defaultdict, OrderedDict
import openpyxl

def main():
    if len(sys.argv) < 2:
        print("Uso: python run_pipeline.py <planilha.xlsx>")
        sys.exit(1)
    SRC = sys.argv[1]
    base = os.path.splitext(os.path.basename(SRC))[0]
    out_dir = os.path.dirname(os.path.abspath(SRC))
    OUT_XLSX = os.path.join(out_dir, base + " - otimizado.xlsx")
    OUT_MD = os.path.join(out_dir, "Relatorio Visual - Rota de Entrega.md")

    wb = openpyxl.load_workbook(SRC)
    ws = wb[wb.sheetnames[0]]
    rows = list(ws.iter_rows(values_only=True))
    header = rows[0]
    data = rows[1:]

    # (pipeline identical to tested version)
    def std_cep(v):
        digits = ''.join(ch for ch in str(v) if ch.isdigit())
        if len(digits) == 8:
            return digits
        return str(v).strip()

    def parse_address(raw):
        s = str(raw).strip()
        s = re.sub(r'\bQ(\d+)LT(\d+)\b', r'Qd \1 Lt \2', s, flags=re.IGNORECASE)
        s = re.sub(r'\bQ(\d+)L(\d+)\b', r'Qd \1 Lt \2', s, flags=re.IGNORECASE)
        s = re.sub(r'\bKD(\d+)LT(\d+)\b', r'Qd \1 Lt \2', s, flags=re.IGNORECASE)
        # normalize colon separators: qd:, lt:, av:, rua:, r:, trav:
        s = re.sub(r'\b(qd|quadra|q)\s*[:.\-]\s*', 'Qd. ', s, flags=re.IGNORECASE)
        s = re.sub(r'\b(lt|lote|lot|l)\s*[:.\-]\s*', 'Lt. ', s, flags=re.IGNORECASE)
        s = re.sub(r'\b(av|avenida)\s*[:.\-]\s*', 'Av. ', s, flags=re.IGNORECASE)
        s = re.sub(r'\b(trav|travessa)\s*[:.\-]\s*', 'Trav. ', s, flags=re.IGNORECASE)
        s = re.sub(r'\b(rua|r)\s*[:.\-]\s*', 'Rua ', s, flags=re.IGNORECASE)
        qd = None
        m = re.search(r'\b(?:kd|qd|quadra|q)[:.\-\s]*([A-Za-z0-9\-]+)', s, re.IGNORECASE)
        if m:
            qd = m.group(1).upper().rstrip('.')
            s = s.replace(m.group(0), ' ', 1)
        lt = None
        m = re.search(r'\b(?:lt|lote|lot|l)[:.\-\s]*([0-9][A-Za-z0-9\-]*)', s, re.IGNORECASE)
        if m:
            lt = m.group(1).upper().rstrip('.')
            s = s.replace(m.group(0), ' ', 1)
        parts = [p.strip() for p in s.split(',') if p.strip()]
        street_idx = None
        for i, p in enumerate(parts):
            first = re.sub(r'[^a-z]', '', p.lower().split()[0]) if p.split() else ''
            if first in ('rua','avenida','av','r','travessa','trav','alameda','al','estrada','rodovia'):
                street_idx = i; break
        if street_idx is None:
            street_idx = 0
        street_part = parts[street_idx] if parts else s.strip()
        street = re.sub(r'^Avenida\b', 'Av.', street_part, flags=re.IGNORECASE)
        street = re.sub(r'^Travessa\b', 'Trav.', street, flags=re.IGNORECASE)
        street = re.sub(r'^R\b(?!\.)', 'R.', street, flags=re.IGNORECASE)
        street = re.sub(r'^Trav\b(?!\.)', 'Trav.', street, flags=re.IGNORECASE)
        street = re.sub(r'\s+', ' ', street).strip()
        NO_NUM = {'sn','s/n','s n','sem','sem n','n/a','n a','-','','0','00','000','0000'}
        numero = None
        obs_parts = []
        for i, p in enumerate(parts):
            if i == street_idx:
                continue
            cand = p.strip()
            low = cand.lower()
            if low in NO_NUM or low.startswith('sem'):
                continue
            if re.search(r'residencial|condominio|cond\.?|bairro|setor|jardim|vila|parque|loteamento', cand, re.IGNORECASE):
                continue
            if numero is None and re.match(r'^\d+[a-z]?(/\d+[a-z]?)?$', cand, re.IGNORECASE):
                numero = cand
            else:
                obs_parts.append(cand)
        obs = re.sub(r'\s+', ' ', ', '.join(obs_parts)).strip()
        comps = [street]
        if qd: comps.append(f'Qd. {qd}')
        if lt: comps.append(f'Lt. {lt}')
        if numero is not None: comps.append(f'nº {numero}')
        if obs: comps.append(obs)
        formatted = ', '.join(comps)
        warns = []
        if not qd: warns.append('faltando quadra')
        if not lt: warns.append('faltando lote')
        if numero is None: warns.append('faltando número')
        return formatted, warns

    def addr_warnings(raw):
        return parse_address(raw)[1]

    def core_key(addr):
        s = str(addr).lower()
        for w in ['rua','avenida','av.','av','travessa','trav.','trav','alameda','al.','al','quadra','qd.','qd','lote','lt.','lt','lot']:
            s = re.sub(r'\b'+re.escape(w)+r'\b', ' ', s)
        s = re.sub(r'q(?=\d)', '', s)
        s = re.sub(r'l(?=\d)', '', s)
        s = re.sub(r'[^a-z0-9]', '', s)
        return s

    import unicodedata
    def building_core(raw):
        s = str(raw)
        # 1. keyword-based: keyword followed by name
        m = re.search(r'(?:cond\.?|condominio|residencial|ed\.?|edificio|pr[eé]dio|torre|bloco|loteamento|conjunto|res\.?)\s+(.+)', s, re.IGNORECASE)
        if m:
            tail = m.group(1)
            tail = re.split(r'\b(?:apto|ap\.?|ap|bl\.?|bloco|apt|apt\.|casa|lt\.?|lote|qd\.?|quadra|b\d)\b', tail, flags=re.IGNORECASE)[0]
            tail = unicodedata.normalize('NFKD', tail).encode('ascii', 'ignore').decode().lower()
            tail = re.sub(r'[^a-z ]', ' ', tail)
            tail = re.sub(r'\s+', ' ', tail).strip()
            if len(tail) >= 3:
                return tail
        # 2. capitalized phrase not in street position
        parts = [p.strip() for p in s.split(',') if p.strip()]
        street_idx = None
        for i, p in enumerate(parts):
            if re.search(r'\b(rua|avenida|av\.?|travessa|alameda|estrada|rodovia)\b', p, re.IGNORECASE):
                street_idx = i; break
        # if no street keyword, consider all parts
        candidate_parts = [p for i, p in enumerate(parts) if i != street_idx] if street_idx is not None else parts
        for p in candidate_parts:
            cleaned = re.sub(r'\b(?:apto|ap\.?|ap|bl\.?|bloco|apt|apt\.|casa|lt\.?|lote|qd\.?|quadra|b\d|nº|no)\b\.?\s*\S*', '', p, flags=re.IGNORECASE)
            cleaned = re.sub(r'\b\d+[-.]?\d*\b', '', cleaned)
            cleaned = cleaned.strip(' -.,')
            if not re.search(r'[A-Z]', cleaned):
                continue
            norm = unicodedata.normalize('NFKD', cleaned).encode('ascii', 'ignore').decode().lower()
            norm = re.sub(r'[^a-z ]', ' ', norm)
            norm = re.sub(r'\s+', ' ', norm).strip()
            if len(norm.split()) >= 2 and len(norm) >= 8:
                return norm
        # 3. whole-string capitalized phrase (no commas)
        if len(parts) == 1:
            cleaned = re.sub(r'\b(?:apto|ap\.?|ap|bl\.?|bloco|apt|apt\.|casa|lt\.?|lote|qd\.?|quadra|b\d|nº|no)\b\.?\s*\S*', '', s, flags=re.IGNORECASE)
            cleaned = re.sub(r'\b\d+[-.]?\d*\b', '', cleaned)
            if re.search(r'[A-Z]', cleaned):
                norm = unicodedata.normalize('NFKD', cleaned).encode('ascii', 'ignore').decode().lower()
                norm = re.sub(r'[^a-z ]', ' ', norm)
                # remove street words
                for w in ['rua','avenida','av','travessa','trav','alameda','al','estrada','rodovia']:
                    norm = re.sub(r'\b'+w+r'\b', '', norm)
                norm = re.sub(r'\s+', ' ', norm).strip()
                if len(norm.split()) >= 2 and len(norm) >= 8:
                    return norm
        return None

    def edit_dist(a, b):
        if a == b: return 0
        if len(a) < len(b): a, b = b, a
        if len(b) == 0: return len(a)
        prev = list(range(len(b)+1))
        for i, ca in enumerate(a):
            cur = [i+1]
            for j, cb in enumerate(b):
                cur.append(min(prev[j+1]+1, cur[j]+1, prev[j]+(ca != cb)))
            prev = cur
        return prev[-1]

    def cores_similar(a, b):
        if a == b: return True
        if a in b or b in a: return True
        # token overlap
        ta = set(a.split()); tb = set(b.split())
        if ta and tb and len(ta & tb) >= 2: return True
        if edit_dist(a, b) <= 2: return True
        return False

    viacep_cache = {}
    def viacep(cep):
        if cep in viacep_cache: return viacep_cache[cep]
        url = f'https://viacep.com.br/ws/{cep}/json/'
        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                d = json.loads(resp.read().decode('utf-8'))
            res = None if 'erro' in d else d
        except Exception as e:
            res = {'_error': str(e)}
        viacep_cache[cep] = res
        time.sleep(0.12)
        return res

    unique_ceps = sorted(set(std_cep(r[7]) for r in data))
    viacep_results = {c: viacep(c) for c in unique_ceps}

    cep_bairro_src = defaultdict(Counter)
    for r in data:
        cep_bairro_src[std_cep(r[7])][str(r[5]).strip()] += 1

    canonical_bairro = {}
    viacep_divergences = []
    for c in unique_ceps:
        res = viacep_results[c]
        src_top = cep_bairro_src[c].most_common(1)[0][0] if c in cep_bairro_src else ''
        if res and not (isinstance(res, dict) and '_error' in res) and res.get('bairro'):
            vc_bairro = res['bairro']
            canonical_bairro[c] = vc_bairro
            if vc_bairro.strip().lower() != src_top.strip().lower():
                viacep_divergences.append((c, src_top, vc_bairro))
        else:
            canonical_bairro[c] = src_top

    coord_groups = defaultdict(list)
    for i, r in enumerate(data):
        coord_groups[(r[8], r[9])].append(i)
    dup_coord = {k: v for k, v in coord_groups.items() if len(v) > 1 and len(set(data[i][4] for i in v)) > 1}

    # compute building core per row
    row_core = [building_core(r[4]) for r in data]
    # union-find clustering of cores within same CEP by similarity
    # map (cep, core) -> cluster representative
    # first, collect unique cores per cep
    cep_cores = defaultdict(set)
    for i, r in enumerate(data):
        c = std_cep(r[7])
        if row_core[i]:
            cep_cores[c].add(row_core[i])
    # canonicalize cores: pick most frequent similar core as representative
    core_freq = Counter()
    for i, r in enumerate(data):
        rc = row_core[i]
        if rc:
            core_freq[rc] += 1
    def canonical_core(c):
        best = c
        best_freq = core_freq.get(c, 0)
        for other, f in core_freq.items():
            if other == c: continue
            if cores_similar(c, other) and f > best_freq:
                best = other; best_freq = f
        return best
    core_canonical = {c: canonical_core(c) for c in core_freq}

    def _correct_addr(addr, rc, cep):
        if not rc:
            return addr
        rep = core_cluster.get((cep, rc), rc)
        rep = core_canonical.get(rep, rep)
        if rep and rep != rc:
            return re.sub(re.escape(rc), rep, addr, flags=re.IGNORECASE)
        return addr

    # cluster cores per cep
    core_cluster = {}  # (cep, core) -> representative core
    for c, cores in cep_cores.items():
        cores = list(cores)
        parent = {x: x for x in cores}
        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x
        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb
        for i in range(len(cores)):
            for j in range(i+1, len(cores)):
                if cores_similar(cores[i], cores[j]):
                    union(cores[i], cores[j])
        for x in cores:
            rep = find(x)
            rep = core_canonical.get(rep, rep)
            core_cluster[(c, x)] = rep

    stops = OrderedDict()
    for i, r in enumerate(data):
        sa = parse_address(r[4])[0]
        c = std_cep(r[7])
        rc = row_core[i]
        if rc:
            rep = core_cluster.get((c, rc), rc)
            key = (c, 'BLD:' + rep)
        else:
            key = (c, core_key(sa))
        stops.setdefault(key, []).append(i)

    def _ql_sort(val):
        v = str(val).strip()
        try:
            return (0, int(v), '')
        except ValueError:
            return (1, 0, v)
    def _stop_sortkey(k):
        addr = parse_address(data[stops[k][0]][4])[0]
        qm = re.search(r'Qd\.?\s*([A-Za-z0-9\-]+)', addr, re.IGNORECASE)
        lm = re.search(r'Lt\.?\s*([A-Za-z0-9\-]+)', addr, re.IGNORECASE)
        q = _ql_sort(qm.group(1)) if qm else (2, 0, '')
        l = _ql_sort(lm.group(1)) if lm else (2, 0, '')
        return (k[0], canonical_bairro[k[0]], core_key(addr), q, l)
    stop_keys_sorted = sorted(stops.keys(), key=_stop_sortkey)

    stop_number = {k: idx for idx, k in enumerate(stop_keys_sorted, start=1)}

    final_rows = []
    for k in stop_keys_sorted:
        idxs = stops[k]
        total = len(idxs)
        cep = k[0]
        cb = canonical_bairro[cep]
        sa = parse_address(data[idxs[0]][4])[0]
        # spelling correction: replace building core variant with canonical spelling
        rc0 = row_core[idxs[0]] if idxs[0] < len(row_core) else None
        if rc0:
            rep = core_cluster.get((std_cep(data[idxs[0]][7]), rc0), rc0)
            rep = core_canonical.get(rep, rep)
            if rep and rep != rc0:
                sa = re.sub(re.escape(rc0), rep, sa, flags=re.IGNORECASE)
        warns0 = addr_warnings(data[idxs[0]][4])
        obs_base = []
        if total > 1: obs_base.append('Mais de 1 pacote no mesmo endereço')
        if len(set(str(data[i][5]).strip() for i in idxs)) > 1: obs_base.append('Bairro com grafias variantes')
        obs_base.extend(warns0)
        for n, i in enumerate(idxs, start=1):
            r = data[i]
            w = list(obs_base)
            for x in addr_warnings(r[4]):
                if x not in w: w.append(x)
            _pa_warns = addr_warnings(r[4])
            if 'faltando quadra' in _pa_warns and 'faltando lote' in _pa_warns and 'faltando número' in _pa_warns:
                w.append('Endereço incompleto — revisar obrigatoriamente')
            final_rows.append({
                'Ordem Otimizada da Rota': stop_number[k],
                'Parada Consolidada': stop_number[k],
                'Número original do Pacote na Parada': n,
                'Quantidade Total de Pacotes na Parada': total,
                'Código do Pacote': r[3],
                'Sequence Original': r[1],
                'Destinatário': '',
                'Endereço Original': r[4],
                'Endereço Padronizado': _correct_addr(parse_address(r[4])[0], row_core[i] if i < len(row_core) else None, std_cep(r[7])),
                'Bairro': cb,
                'Cidade': r[6],
                'CEP': cep,
                'Latitude': r[8],
                'Longitude': r[9],
                'Observações': '; '.join(w),
            })

    out_wb = openpyxl.Workbook()
    out_wb.remove(out_wb.active)

    cols = ['Ordem Otimizada da Rota','Parada Consolidada','Número original do Pacote na Parada',
            'Quantidade Total de Pacotes na Parada','Código do Pacote','Sequence Original',
            'Destinatário','Endereço Original','Endereço Padronizado','Bairro','Cidade','CEP',
            'Latitude','Longitude','Observações']
    wsf = out_wb.create_sheet('Rota Otimizada')
    wsf.append(cols)
    for fr in final_rows:
        wsf.append([fr[c] for c in cols])

    ws0 = out_wb.create_sheet('Dados Originais')
    ws0.append(list(header))
    for r in data:
        ws0.append(list(r))

    wsc = out_wb.create_sheet('Coordenadas Suspeitas')
    wsc.append(['Endereço','Latitude','Longitude','Motivo da suspeita'])
    seen = set()
    for coord, idxs in dup_coord.items():
        for i in idxs:
            r = data[i]
            key = (r[4], r[8], r[9])
            if key in seen: continue
            seen.add(key)
            wsc.append([r[4], r[8], r[9], 'Coordenada compartilhada por múltiplos endereços distintos'])

    wsc2 = out_wb.create_sheet('CEPs Faltantes')
    wsc2.append(['CEP Original','CEP Padronizado','Status','Quantidade'])
    missing = [r for r in data if len(''.join(ch for ch in str(r[7]) if ch.isdigit())) != 8]
    wsc2.append(['-', '-', 'Nenhum CEP faltante ou incompleto encontrado', len(missing)])

    wsv = out_wb.create_sheet('ViaCEP')
    wsv.append(['CEP','Logradouro (ViaCEP)','Bairro (ViaCEP)','Localidade (ViaCEP)','UF','Status'])
    for c in unique_ceps:
        res = viacep_results[c]
        if res is None:
            wsv.append([c, '', '', '', '', 'CEP não encontrado'])
        elif isinstance(res, dict) and '_error' in res:
            wsv.append([c, '', '', '', '', f"Erro: {res['_error']}"])
        else:
            wsv.append([c, res.get('logradouro',''), res.get('bairro',''), res.get('localidade',''), res.get('uf',''), 'OK'])

    wsa = out_wb.create_sheet('Auditoria')
    wsa.append(['Categoria','Detalhe','Quantidade'])
    for c, src_top, vc in viacep_divergences:
        wsa.append(['Bairro divergente (planilha vs ViaCEP)', f'{c}: planilha="{src_top}" vs ViaCEP="{vc}"', 1])
    merged_groups = [k for k, v in stops.items() if len(v) > 1]
    wsa.append(['Endereços consolidados (mesma parada)', 'grupos', len(merged_groups)])
    wsa.append(['Total de pacotes consolidados', 'pacotes', sum(len(stops[k]) for k in merged_groups)])
    wsa.append(['Coordenadas compartilhadas por endereços distintos', 'grupos', len(dup_coord)])

    by_bairro = OrderedDict()
    for k in stop_keys_sorted:
        r0 = data[stops[k][0]]
        cep = k[0]
        cb = canonical_bairro[cep]
        by_bairro.setdefault(cb, []).append(k)

    lines = []
    lines.append('SEQUÊNCIA DAS ENTREGAS - ROTA COMPLETA')
    lines.append(f'TOTAL: {len(stop_keys_sorted)} PARADAS  |  {len(data)} PACOTES  (CONFORME PLANILHA SHOPEE)')
    lines.append('')
    lines.append('LEGENDA:')
    lines.append('Nº Shopee = parada original da Shopee (STOP)')
    lines.append('Nº Azul = nossa numeração de entrega')
    lines.append('Mais de 1 pacote no mesmo endereço = parada consolidada')
    lines.append('Bairro padronizado via ViaCEP; endereço no formato Nome da rua, Qd., Lt., nº, Observação')
    lines.append('')
    for bairro, ks in by_bairro.items():
        lines.append(bairro.upper())
        for k in ks:
            idxs = stops[k]
            sn = stop_number[k]
            total = len(idxs)
            sa = parse_address(data[idxs[0]][4])[0]
            cep = k[0]
            seqs = ', '.join(str(data[i][1]) for i in idxs)
            lines.append(f'  Parada {sn} | {sa} | {seqs} | {total} pac')
        lines.append('')
    lines.append('RESUMO DAS PARADAS COM MAIS DE 1 PACOTE')
    for k in stop_keys_sorted:
        idxs = stops[k]
        if len(idxs) > 1:
            sa = parse_address(data[idxs[0]][4])[0]
            cep = k[0]
            cb = canonical_bairro[cep]
            codes = ', '.join(str(data[i][3]) for i in idxs)
            seqs = ', '.join(str(data[i][1]) for i in idxs)
            lines.append(f'  Parada {stop_number[k]} | {cb} | {sa} | CEP {cep} | Pacotes: {codes} | Seq: {seqs} ({len(idxs)})')

    wsr = out_wb.create_sheet('Relatorio Visual')
    for ln in lines:
        wsr.append([ln])

    out_wb.save(OUT_XLSX)
    with open(OUT_MD, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print('rows', len(data))
    print('stops', len(stop_keys_sorted))
    print('packages', len(data))
    print('reduction', len(data)-len(stop_keys_sorted), round((1-len(stop_keys_sorted)/len(data))*100,1),'%')
    print('merged groups', len(merged_groups), 'pkgs', sum(len(stops[k]) for k in merged_groups))
    print('coord dup groups', len(dup_coord))
    print('viacep divergences', len(viacep_divergences))
    print('saved', OUT_XLSX)
    print('saved', OUT_MD)

if __name__ == '__main__':
    main()