/*
 * Cadastro de máquinas: usa a API /api/catalogo para sugerir marca, modelo,
 * intervalo de revisão e valor de referência de cada tipo de máquina.
 */
document.addEventListener("DOMContentLoaded", function () {
  const form = document.getElementById("form-maquina");
  if (!form) return;

  const api = form.dataset.api;
  const porTipo = JSON.parse(form.dataset.porTipo || "{}");
  const editando = form.dataset.editando === "1";

  const campo = (id) => document.getElementById(id);
  const tipo = campo("tipo");
  const nome = campo("nome");
  const marca = campo("marca");
  const modelo = campo("modelo");
  const revisao = campo("revisao_horas");
  const preco = campo("preco");
  const precoReferencia = campo("preco-referencia");
  const listaMarcas = campo("lista-marcas");
  const listaModelos = campo("lista-modelos");
  const ficha = campo("ficha-tipo");
  const busca = campo("busca");
  const resultados = campo("busca-resultados");

  let dadosTipo = null;

  function reais(valor) {
    return valor.toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
  }

  function preencherLista(lista, valores) {
    lista.replaceChildren(...valores.map(function (v) {
      const opcao = document.createElement("option");
      opcao.value = v;
      return opcao;
    }));
  }

  function nomeSugerido() {
    const numero = String((porTipo[tipo.value] || 0) + 1).padStart(2, "0");
    return dadosTipo.nome + " " + numero;
  }

  // Modelos da marca digitada (ou de todas as marcas do tipo, se a marca não estiver no catálogo)
  function atualizarModelos() {
    const texto = marca.value.trim().toLowerCase();
    const achada = dadosTipo.marcas.find((m) => m.nome.toLowerCase() === texto);
    preencherLista(listaModelos, achada ? achada.modelos : dadosTipo.marcas.flatMap((m) => m.modelos));
  }

  function mostrarFicha() {
    const d = dadosTipo;
    const linhas = [["Revisão preventiva", "a cada " + d.revisao_horas + " h"]];
    if (d.vida_util) linhas.push(["Vida útil estimada", d.vida_util.toLocaleString("pt-BR") + " h"]);
    if (d.horas_ano) linhas.push(["Uso típico", d.horas_ano + " h/ano"]);
    if (d.preco_referencia) linhas.push(["Preço de referência (nova)", reais(d.preco_referencia)]);

    const titulo = document.createElement("h3");
    titulo.textContent = d.icone + " " + d.nome;

    const dados = document.createElement("div");
    dados.className = "dados-maquina";
    linhas.forEach(function ([rotulo, valor]) {
      const linha = document.createElement("div");
      const r = document.createElement("span");
      const v = document.createElement("strong");
      r.textContent = rotulo;
      v.textContent = valor;
      linha.append(r, v);
      dados.append(linha);
    });

    const subtitulo = document.createElement("p");
    subtitulo.className = "suave";
    subtitulo.textContent = "Checklist preventivo (aparece na aba Manutenção):";
    const itens = document.createElement("ul");
    d.itens_preventivos.forEach(function (i) {
      const li = document.createElement("li");
      li.textContent = i;
      itens.append(li);
    });

    ficha.replaceChildren(titulo, dados, subtitulo, itens);
  }

  async function carregarTipo() {
    const resposta = await fetch(api + "/" + encodeURIComponent(tipo.value));
    if (!resposta.ok) return;
    dadosTipo = await resposta.json();

    preencherLista(listaMarcas, dadosTipo.marcas.map((m) => m.nome));
    atualizarModelos();
    mostrarFicha();

    revisao.placeholder = "Padrão: " + dadosTipo.revisao_horas;
    if (!editando) nome.placeholder = "Ex.: " + nomeSugerido();
    precoReferencia.textContent = dadosTipo.preco_referencia
      ? "Referência de uma nova: " + reais(dadosTipo.preco_referencia)
      : "";
  }

  tipo.addEventListener("change", carregarTipo);
  marca.addEventListener("input", atualizarModelos);

  // Sem apelido, usa o nome sugerido (ex.: "Trator cafeeiro 02")
  form.addEventListener("submit", function () {
    if (!editando && !nome.value.trim() && dadosTipo) nome.value = nomeSugerido();
  });

  // ===== Busca no catálogo =====
  if (busca) {
    let espera = null;

    async function buscar() {
      const q = busca.value.trim();
      if (q.length < 2) {
        resultados.hidden = true;
        return;
      }
      const resposta = await fetch(api + "/busca?q=" + encodeURIComponent(q));
      const achados = await resposta.json();

      resultados.replaceChildren(...achados.map(function (a) {
        const li = document.createElement("li");
        const botao = document.createElement("button");
        botao.type = "button";
        botao.innerHTML = "<strong></strong> <span class='suave'></span>";
        botao.querySelector("strong").textContent = a.marca + " " + a.modelo;
        botao.querySelector("span").textContent = a.tipo_nome;
        botao.addEventListener("click", async function () {
          tipo.value = a.tipo;
          await carregarTipo();
          marca.value = a.marca;
          modelo.value = a.modelo;
          atualizarModelos();
          busca.value = "";
          resultados.hidden = true;
          campo("ano").focus();
        });
        li.append(botao);
        return li;
      }));
      if (!achados.length) {
        const li = document.createElement("li");
        li.className = "suave";
        li.textContent = "Nenhum modelo encontrado. Preencha os campos abaixo.";
        resultados.append(li);
      }
      resultados.hidden = false;
    }

    busca.addEventListener("input", function () {
      clearTimeout(espera);
      espera = setTimeout(buscar, 250);
    });
  }

  carregarTipo();
});
