/*
 * CRUD pela API REST (rotas/api.py), usando o método HTTP certo para cada operação:
 *
 *   <form data-rest="/api/maquinas" data-metodo="POST">        cadastrar  (POST)
 *   <form data-rest="/api/maquinas/3" data-metodo="PUT">       editar     (PUT)
 *   <button data-rest="/api/maquinas/3" data-metodo="PATCH"
 *           data-corpo='{"ativo": 0}'>                         desativar  (PATCH)
 *   <button data-rest="/api/maquinas/3" data-metodo="DELETE"
 *           data-confirmar="Excluir esta máquina?">            excluir    (DELETE)
 *
 * Toda requisição leva o token CSRF no cabeçalho X-CSRF-Token.
 * Deu certo: a página recarrega (ou vai para "redirecionar") e mostra o aviso.
 * Deu errado: a mensagem de erro aparece na tela, sem perder o que foi digitado.
 */
(function () {
  const token = document.querySelector('meta[name="csrf-token"]');

  async function enviar(url, metodo, corpo) {
    const resposta = await fetch(url, {
      method: metodo,
      headers: {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-CSRF-Token": token ? token.content : "",
      },
      credentials: "same-origin",
      body: corpo ? JSON.stringify(corpo) : undefined,
    });
    let dados = {};
    try {
      dados = await resposta.json();
    } catch (e) {
      dados = { erro: "Resposta inesperada do servidor (" + resposta.status + ")." };
    }
    return { ok: resposta.ok, dados: dados };
  }

  /* Mostra o erro numa caixa no topo do formulário (ou da página) */
  function mostrarErro(alvo, dados) {
    const lista = dados.erros && dados.erros.length ? dados.erros : [dados.erro || "Não foi possível salvar."];
    let caixa = alvo.querySelector(":scope > .alerta.erro.crud");
    if (!caixa) {
      caixa = document.createElement("div");
      caixa.className = "alerta erro crud";
      caixa.setAttribute("role", "alert");
      alvo.prepend(caixa);
    }
    caixa.replaceChildren(...lista.map(function (texto) {
      const linha = document.createElement("div");
      linha.textContent = texto;
      return linha;
    }));
    caixa.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  function concluir(dados) {
    if (dados.redirecionar) window.location.href = dados.redirecionar;
    else window.location.reload();
  }

  /* Lê os campos do formulário como objeto; checkbox vira true/false */
  function dadosDoFormulario(form) {
    const dados = {};
    new FormData(form).forEach(function (valor, chave) {
      if (chave !== "csrf") dados[chave] = valor;
    });
    form.querySelectorAll('input[type="checkbox"][name]').forEach(function (caixa) {
      dados[caixa.name] = caixa.checked;
    });
    return dados;
  }

  document.addEventListener("submit", async function (evento) {
    const form = evento.target.closest("form[data-rest]");
    if (!form) return;
    evento.preventDefault();

    const botao = form.querySelector('button[type="submit"], button:not([type])');
    if (botao) botao.disabled = true;
    try {
      const r = await enviar(form.dataset.rest, form.dataset.metodo || "POST", dadosDoFormulario(form));
      if (r.ok) return concluir(r.dados);
      mostrarErro(form, r.dados);
    } catch (e) {
      mostrarErro(form, { erro: "Sem conexão com o servidor. Tente novamente." });
    }
    if (botao) botao.disabled = false;
  });

  document.addEventListener("click", async function (evento) {
    const botao = evento.target.closest("button[data-rest]");
    if (!botao || botao.form && botao.form.dataset.rest) return;
    evento.preventDefault();
    if (botao.dataset.confirmar && !window.confirm(botao.dataset.confirmar)) return;

    botao.disabled = true;
    try {
      const corpo = botao.dataset.corpo ? JSON.parse(botao.dataset.corpo) : null;
      const r = await enviar(botao.dataset.rest, botao.dataset.metodo || "POST", corpo);
      if (r.ok) return concluir(r.dados);
      mostrarErro(document.querySelector("main .container, main") || document.body, r.dados);
    } catch (e) {
      mostrarErro(document.querySelector("main .container, main") || document.body,
                  { erro: "Sem conexão com o servidor. Tente novamente." });
    }
    botao.disabled = false;
  });
})();
