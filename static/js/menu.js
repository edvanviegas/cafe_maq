/* Abre e fecha o menu no celular */
document.addEventListener("DOMContentLoaded", function () {
  const botao = document.querySelector(".menu-botao");
  const menu = document.querySelector(".menu");

  if (botao && menu) {
    botao.addEventListener("click", function () {
      menu.classList.toggle("aberto");
    });
  }

  // Botão "Voltar": volta à página anterior do site; sem histórico, vai para o início (href)
  const voltar = document.querySelector("[data-voltar]");
  if (voltar) {
    voltar.addEventListener("click", function (evento) {
      const veioDoSite = document.referrer.indexOf(window.location.origin) === 0;
      if (veioDoSite && window.history.length > 1) {
        evento.preventDefault();
        window.history.back();
      }
    });
  }

  const ano = document.getElementById("ano");
  if (ano) ano.textContent = new Date().getFullYear();
});
