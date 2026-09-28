"""
Catálogo de máquinas da cafeicultura, servido pela API /api/catalogo.

É usado no cadastro de máquinas (sugere marca, modelo, intervalo de revisão e
valor de referência) e na aba Manutenção (checklist preventivo de cada tipo).

Preço, vida útil e uso anual são os mesmos valores de referência de
static/js/dados.js (estimativas baseadas na ASABE D497). A lista de marcas e
modelos é um ponto de partida: acrescente os modelos usados na sua região.
Marcas sem modelos listados continuam aceitando o modelo digitado livremente.
"""

TIPOS = {
    'trator': {
        'nome': 'Trator cafeeiro',
        'icone': '🚜',
        'revisao': 250,
        'preco_referencia': 230000,
        'vida_util': 12000,
        'horas_ano': 800,
        'itens_preventivos': [
            'Troca de óleo do motor',
            'Troca dos filtros de ar, óleo e combustível',
            'Engraxar articulações',
            'Verificar pressão dos pneus e correias',
        ],
    },
    'colhedora': {
        'nome': 'Colhedora automotriz',
        'icone': '🌿',
        'revisao': 150,
        'preco_referencia': 1300000,
        'vida_util': 3000,
        'horas_ano': 450,
        'itens_preventivos': [
            'Revisão completa antes da safra',
            'Troca de varetas vibratórias danificadas',
            'Verificar sistema hidráulico e mangueiras',
            'Limpeza de esteiras e ventiladores',
        ],
    },
    'colhedora-tracionada': {
        'nome': 'Colhedora tracionada',
        'icone': '⚙️',
        'revisao': 150,
        'preco_referencia': 420000,
        'vida_util': 3000,
        'horas_ano': 400,
        'itens_preventivos': [
            'Lubrificação do cardã e caixas de engrenagem',
            'Inspeção de varetas e cilindros derriçadores',
            'Aperto de parafusos e rolamentos',
            'Verificar esteiras transportadoras',
        ],
    },
    'pulverizador': {
        'nome': 'Pulverizador',
        'icone': '💨',
        'revisao': 100,
        'preco_referencia': 95000,
        'vida_util': 2000,
        'horas_ano': 300,
        'itens_preventivos': [
            'Lavar tanque e circuito',
            'Calibrar e trocar bicos desgastados',
            'Verificar bomba, filtros e manômetro',
            'Inspecionar hélice e rolamentos do ventilador',
        ],
    },
    'rocadeira': {
        'nome': 'Roçadeira',
        'icone': '🌾',
        'revisao': 100,
        'preco_referencia': 38000,
        'vida_util': 2000,
        'horas_ano': 250,
        'itens_preventivos': [
            'Afiar ou trocar facas',
            'Verificar óleo da caixa de transmissão',
            'Engraxar cardã e rolamentos',
            'Checar parafusos das facas',
        ],
    },
    'adubadora': {
        'nome': 'Adubadora / distribuidora',
        'icone': '🧪',
        'revisao': 100,
        'preco_referencia': 45000,
        'vida_util': 1200,
        'horas_ano': 150,
        'itens_preventivos': [
            'Lavar após o uso (adubo é corrosivo)',
            'Aplicar óleo protetivo nas partes metálicas',
            'Verificar esteira e dosador',
            'Trocar correntes desgastadas',
        ],
    },
    'derricadeira': {
        'nome': 'Derriçadeira portátil',
        'icone': '🔧',
        'revisao': 50,
        'preco_referencia': 4500,
        'vida_util': 1500,
        'horas_ano': 400,
        'itens_preventivos': [
            'Limpar filtro de ar',
            'Verificar vela de ignição',
            'Conferir mistura de combustível e óleo 2T',
            'Trocar hastes/dedos quebrados',
        ],
    },
    'outra': {
        'nome': 'Outra',
        'icone': '🛠️',
        'revisao': 250,
        'preco_referencia': None,
        'vida_util': None,
        'horas_ano': None,
        'itens_preventivos': [
            'Troca de óleo e filtros',
            'Lubrificação geral',
            'Inspeção visual e aperto de parafusos',
        ],
    },
}

# tipo -> marca -> lista de modelos
MODELOS = {
    'trator': {
        'Massey Ferguson': ['MF 4265', 'MF 4275', 'MF 4707'],
        'New Holland': ['TT3840F', 'TT4030', 'TL75E'],
        'Valtra': ['A750'],
        'John Deere': ['5075E', '5078E'],
        'Agrale': ['5075.4'],
        'LS Tractor': ['U60'],
    },
    'colhedora': {
        'Jacto': ['K3 Millennium', 'K3500'],
        'Case IH': ['Coffee Express 200'],
    },
    'colhedora-tracionada': {
        'Jacto': ['KTR Advance'],
    },
    'pulverizador': {
        'Jacto': ['Arbus 2000', 'Arbus 4000'],
    },
    'rocadeira': {
        'Kamaq': [],
        'Tatu Marchesan': [],
    },
    'adubadora': {
        'Kuhn': [],
        'Lavrale': [],
        'Tatu Marchesan': [],
    },
    'derricadeira': {
        'Stihl': ['SP 451', 'SP 481'],
    },
    'outra': {},
}


def nome_tipo(tipo):
    return TIPOS.get(tipo, {}).get('nome', tipo)


def intervalo_revisao(maquina):
    """Intervalo de revisão da máquina: o definido no cadastro ou o padrão do tipo."""
    return maquina.get('revisao_horas') or TIPOS.get(maquina['tipo'], TIPOS['outra'])['revisao']


def ficha_tipo(tipo):
    """Dados de um tipo no formato da API."""
    t = TIPOS[tipo]
    return {
        'tipo': tipo,
        'nome': t['nome'],
        'icone': t['icone'],
        'revisao_horas': t['revisao'],
        'preco_referencia': t['preco_referencia'],
        'vida_util': t['vida_util'],
        'horas_ano': t['horas_ano'],
        'itens_preventivos': t['itens_preventivos'],
        'marcas': [{'nome': marca, 'modelos': modelos} for marca, modelos in MODELOS.get(tipo, {}).items()],
    }


def buscar_modelos(texto, limite=10):
    """Procura por marca ou modelo em todos os tipos (ex.: 'arbus', 'jacto k3')."""
    termos = texto.lower().split()
    if not termos:
        return []
    achados = []
    for tipo, marcas in MODELOS.items():
        for marca, modelos in marcas.items():
            for modelo in modelos:
                completo = f'{marca} {modelo} {TIPOS[tipo]["nome"]}'.lower()
                if all(t in completo for t in termos):
                    achados.append({'tipo': tipo, 'tipo_nome': TIPOS[tipo]['nome'], 'marca': marca, 'modelo': modelo})
    return achados[:limite]
