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
        qd = None
        m = re.search(r'\b(?:kd|qd|quadra|q)\.?\s*([A-Za-z0-9\-]+)', s, re.IGNORECASE)
        if m:
            qd = m.group(1).upper().rstrip('.')
            s = s.replace(m.group(0), ' ', 1)
        lt = None
        m = re.search(r'\b(?:lt|lote|lot|l)\.?\s*([0-9][A-Za-z0-9\-]*)', s, re.IGNORECASE)
        if m:
            lt = m.group(1).upper().rstrip('.')
            s = s.replace(m.group(0), ' ', 1)
        parts = [p.strip() for p in s.split(',') if p.strip()]
        street_idx = None
        for i, p in enumerate(parts):
            first = re.sub(r'[^a-z]', '', p.lower().split()[0]) if p.split() else ''
            if first in ('rua','avenida','av','travessa','trav','alameda','al','estrada','rodovia'):
                street_idx = i; break
        if street_idx is None:
            street_idx = 0
        street_part = parts[street_idx] if parts else s.strip()
        street = re.sub(r'^Avenida\b', 'Av.', street_part, flags=re.IGNORECASE)
        street = re.sub(r'^Travessa\b', 'Trav.', street, flags=re.IGNORECASE)
        street = re.sub(r'^R\b(?!\.)', 'R.', street, flags=re.IGNORECASE)
        street = re.sub(r'^Trav\b(?!\.)', 'Trav.', street, flags=re.IGNORECASE)
        street = re.sub(r'\s+', ' ', street).strip()
        NO_NUM = {'sn','s/n','s n','sem','sem n','n/a','n a','-',''}
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

    stops = OrderedDict()
    for i, r in enumerate(data):
        sa = parse_address(r[4])[0]
        key = (std_cep(r[7]), core_key(sa))
        stops.setdefault(key, []).append(i)

    stop_keys_sorted = sorted(stops.keys(), key=lambda k: (k[0], canonical_bairro[k[0]], core_key(parse_address(data[stops[k][0]][4])[0])))

    stop_number = {k: idx for idx, k in enumerate(stop_keys_sorted, start=1)}

    final_rows = []
    for k in stop_keys_sorted:
        idxs = stops[k]
        total = len(idxs)
        cep = k[0]
        cb = canonical_bairro[cep]
        sa = parse_address(data[idxs[0]][4])[0]
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
                'Endereço Padronizado': parse_address(r[4])[0],
                'Bairro': cb,
                'Cidade': r[6],
                'CEP': cep,
                'Latitude': r[8],
                'Longitude': r[9],
                'Observações': '; '.join(w),
            })

    out_wb = openpyxl.Workbook()
    out_wb.remove(out_wb.active)

    ws0 = out_wb.create_sheet('Dados Originais')
    ws0.append(list(header))
    for r in data:
        ws0.append(list(r))

    cols = ['Ordem Otimizada da Rota','Parada Consolidada','Número original do Pacote na Parada',
            'Quantidade Total de Pacotes na Parada','Código do Pacote','Sequence Original',
            'Destinatário','Endereço Original','Endereço Padronizado','Bairro','Cidade','CEP',
            'Latitude','Longitude','Observações']
    wsf = out_wb.create_sheet('Planilha Final')
    wsf.append(cols)
    for fr in final_rows:
        wsf.append([fr[c] for c in cols])

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
            for n, i in enumerate(idxs, start=1):
                r = data[i]
                flag = '  (mais de 1 pacote)' if total > 1 else ''
                lines.append(f'  Parada {sn} | {sa} | Seq {r[1]} | {total} pac{flag}')
            if total > 1:
                lines.append(f'     -> {total} pacotes no mesmo endereço (Seq: {seqs})')
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