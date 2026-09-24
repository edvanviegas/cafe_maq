/* Lógica da calculadora de custos de manutenção */

const campos = {
  maquina: document.getElementById("maquina"),
  preco: document.getElementById("preco"),
  horasAno: document.getElementById("horasAno"),
  horasUsadas: document.getElementById("horasUsadas"),
  consumo: document.getElementById("consumo"),
  precoCombustivel: document.getElementById("precoCombustivel"),
  sacas: document.getElementById("sacas")
};

function numero(campo) {
  const valor = parseFloat(campo.value);
  return isNaN(valor) || valor < 0 ? 0 : valor;
}

function maquinaSelecionada() {
  return MAQUINAS.find(function (m) { return m.id === campos.maquina.value; });
}

/* Preenche o formulário com os valores padrão da máquina escolhida */
function carregarPadroes() {
  const m = maquinaSelecionada();
  campos.preco.value = m.preco;
  campos.horasAno.value = m.horasAno;
  campos.consumo.value = m.consumo;
  campos.precoCombustivel.value = PRECO_COMBUSTIVEL[m.combustivel].toFixed(2);
  calcular();
}

function calcular() {
  const m = maquinaSelecionada();
  const preco = numero(campos.preco);
  const horasAno = numero(campos.horasAno);
  const horasUsadas = numero(campos.horasUsadas);
  const sacas = numero(campos.sacas);

  const reparo = reparoNoPeriodo(m, preco, horasUsadas, horasAno);
  const combustivel = numero(campos.consumo) * numero(campos.precoCombustivel) * horasAno;
  const lubrificante = combustivel * FATOR_LUBRIFICANTE;
  const total = reparo + combustivel + lubrificante;

  document.getElementById("res-total").textContent = formatarReais(total);
  document.getElementById("res-hora").textContent =
    horasAno > 0 ? formatarReais(total / horasAno) + " por hora trabalhada" : "";
  document.getElementById("res-reparo").textContent = formatarReais(reparo);
  document.getElementById("res-lubrificante").textContent = formatarReais(lubrificante);
  document.getElementById("res-combustivel").textContent = formatarReais(combustivel);
  document.getElementById("res-saca").textContent = sacas > 0 ? formatarReais(total / sacas) : "—";

  const restante = m.vidaUtil - horasUsadas;
  document.getElementById("res-vida").textContent = restante > 0
    ? restante.toLocaleString("pt-BR") + " h (~" + (horasAno > 0 ? (restante / horasAno).toLocaleString("pt-BR", { maximumFractionDigits: 1 }) : "—") + " anos)"
    : "Vida útil atingida — avalie a troca";

  montarProjecao(m, preco, horasUsadas, horasAno);
}

function montarProjecao(m, preco, horasUsadas, horasAno) {
  const linhas = [];
  for (let ano = 1; ano <= 5; ano++) {
    const inicio = horasUsadas + (ano - 1) * horasAno;
    linhas.push({ ano: ano, horimetro: inicio + horasAno, valor: reparoNoPeriodo(m, preco, inicio, horasAno) });
  }

  const maior = Math.max.apply(null, linhas.map(function (l) { return l.valor; })) || 1;

  document.getElementById("tabela-projecao").innerHTML = linhas.map(function (l) {
    const largura = Math.round((l.valor / maior) * 100);
    return "<tr>" +
      "<td>" + l.ano + "º</td>" +
      "<td>" + l.horimetro.toLocaleString("pt-BR") + " h</td>" +
      "<td>" + formatarReais(l.valor) + "</td>" +
      '<td style="width:40%"><div class="barra" style="width:' + largura + '%"></div></td>' +
    "</tr>";
  }).join("");
}

/* Inicialização */
MAQUINAS.forEach(function (m) {
  const opcao = document.createElement("option");
  opcao.value = m.id;
  opcao.textContent = m.icone + " " + m.nome;
  campos.maquina.appendChild(opcao);
});

// Permite abrir já com uma máquina escolhida: calculadora.html?maquina=trator
const parametro = new URLSearchParams(window.location.search).get("maquina");
if (parametro && MAQUINAS.some(function (m) { return m.id === parametro; })) {
  campos.maquina.value = parametro;
}

campos.maquina.addEventListener("change", carregarPadroes);
document.getElementById("form-calculo").addEventListener("input", function (e) {
  if (e.target !== campos.maquina) calcular();
});
document.getElementById("form-calculo").addEventListener("submit", function (e) { e.preventDefault(); });

carregarPadroes();
