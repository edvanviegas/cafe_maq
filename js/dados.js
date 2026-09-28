/*
 * Base de dados das máquinas.
 *
 * Os coeficientes de reparo (rf1, rf2) e a vida útil seguem a norma
 * ASABE D497 (Agricultural Machinery Management Data), adaptados para
 * as máquinas usadas na cafeicultura. Preços e consumos são ESTIMATIVAS
 * de referência — atualize com cotações reais antes de apresentar.
 *
 * Campos:
 *   preco      -> preço de compra da máquina nova (R$)
 *   vidaUtil   -> vida útil estimada (horas)
 *   rf1, rf2   -> fatores de reparo ASABE
 *   consumo    -> consumo médio de combustível (litros/hora)
 *   combustivel-> "diesel" ou "gasolina"
 *   horasAno   -> uso anual típico (horas)
 */
const MAQUINAS = [
  {
    id: "trator",
    nome: "Trator cafeeiro (75–80 cv)",
    icone: "🚜",
    descricao: "Trator estreito usado para tracionar implementos entre as linhas do cafezal.",
    preco: 230000,
    vidaUtil: 12000,
    rf1: 0.007,
    rf2: 2.0,
    consumo: 7.5,
    combustivel: "diesel",
    horasAno: 800,
    itensPreventivos: [
      "Troca de óleo do motor a cada 250 h",
      "Filtros de ar, óleo e combustível",
      "Engraxar articulações diariamente",
      "Verificar pressão dos pneus e correias"
    ]
  },
  {
    id: "colhedora",
    nome: "Colhedora automotriz de café",
    icone: "🌿",
    descricao: "Máquina de grande porte que colhe o café por vibração das hastes, montada sobre a linha.",
    preco: 1300000,
    vidaUtil: 3000,
    rf1: 0.11,
    rf2: 1.8,
    consumo: 12,
    combustivel: "diesel",
    horasAno: 450,
    itensPreventivos: [
      "Revisão completa antes da safra",
      "Troca de varetas vibratórias danificadas",
      "Verificar sistema hidráulico e mangueiras",
      "Limpeza de esteiras e ventiladores"
    ]
  },
  {
    id: "colhedora-tracionada",
    nome: "Colhedora tracionada de café",
    icone: "⚙️",
    descricao: "Colhedora acoplada ao trator, opção mais acessível para médias propriedades.",
    preco: 420000,
    vidaUtil: 3000,
    rf1: 0.11,
    rf2: 1.8,
    consumo: 0,
    combustivel: "diesel",
    horasAno: 400,
    itensPreventivos: [
      "Lubrificação do cardã e caixas de engrenagem",
      "Inspeção de varetas e cilindros derriçadores",
      "Aperto de parafusos e rolamentos",
      "Verificar esteiras transportadoras"
    ]
  },
  {
    id: "pulverizador",
    nome: "Pulverizador turboatomizador (2.000 L)",
    icone: "💨",
    descricao: "Aplica defensivos e foliares com jato de ar, cobrindo toda a copa do cafeeiro.",
    preco: 95000,
    vidaUtil: 2000,
    rf1: 0.20,
    rf2: 1.6,
    consumo: 0,
    combustivel: "diesel",
    horasAno: 300,
    itensPreventivos: [
      "Lavar tanque e circuito após cada uso",
      "Calibrar e trocar bicos desgastados",
      "Verificar bomba, filtros e manômetro",
      "Inspecionar hélice e rolamentos do ventilador"
    ]
  },
  {
    id: "rocadeira",
    nome: "Roçadeira central / lateral",
    icone: "🌾",
    descricao: "Controle do mato nas entrelinhas, acoplada ao trator.",
    preco: 38000,
    vidaUtil: 2000,
    rf1: 0.44,
    rf2: 2.0,
    consumo: 0,
    combustivel: "diesel",
    horasAno: 250,
    itensPreventivos: [
      "Afiar ou trocar facas",
      "Verificar óleo da caixa de transmissão",
      "Engraxar cardã e rolamentos",
      "Checar parafusos das facas"
    ]
  },
  {
    id: "adubadora",
    nome: "Adubadora / distribuidora",
    icone: "🧪",
    descricao: "Distribui fertilizantes e corretivos ao longo das linhas de plantio.",
    preco: 45000,
    vidaUtil: 1200,
    rf1: 0.95,
    rf2: 1.3,
    consumo: 0,
    combustivel: "diesel",
    horasAno: 150,
    itensPreventivos: [
      "Lavar após o uso (adubo é corrosivo)",
      "Aplicar óleo protetivo nas partes metálicas",
      "Verificar esteira e dosador",
      "Trocar correntes desgastadas"
    ]
  },
  {
    id: "derricadeira",
    nome: "Derriçadeira portátil",
    icone: "🔧",
    descricao: "Equipamento costal/manual para colheita semimecanizada em áreas de montanha.",
    preco: 4500,
    vidaUtil: 1500,
    rf1: 0.50,
    rf2: 1.5,
    consumo: 0.9,
    combustivel: "gasolina",
    horasAno: 400,
    itensPreventivos: [
      "Limpar filtro de ar diariamente",
      "Verificar vela de ignição",
      "Usar mistura correta de combustível e óleo 2T",
      "Trocar hastes/dedos quebrados"
    ]
  }
];

/* Preços padrão de combustível (R$/litro) — editáveis na calculadora */
const PRECO_COMBUSTIVEL = {
  diesel: 6.20,
  gasolina: 6.40
};

/* Lubrificantes: ASABE recomenda estimar como 15% do gasto com combustível */
const FATOR_LUBRIFICANTE = 0.15;

function formatarReais(valor) {
  return valor.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

/*
 * Custo de reparo acumulado (fórmula ASABE D497):
 *   CRA = RF1 × P × (h / 1000) ^ RF2
 */
function reparoAcumulado(maquina, preco, horas) {
  return maquina.rf1 * preco * Math.pow(horas / 1000, maquina.rf2);
}

/* Custo de reparo de um período: diferença entre o acumulado no fim e no início */
function reparoNoPeriodo(maquina, preco, horasInicio, horasNoPeriodo) {
  return reparoAcumulado(maquina, preco, horasInicio + horasNoPeriodo)
       - reparoAcumulado(maquina, preco, horasInicio);
}
