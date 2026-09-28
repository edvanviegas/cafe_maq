/* Abre e fecha o menu no celular */
document.addEventListener("DOMContentLoaded", function () {
  const botao = document.querySelector(".menu-botao");
  const menu = document.querySelector(".menu");

  if (botao && menu) {
    botao.addEventListener("click", function () {
      menu.classList.toggle("aberto");
    });
  }

  const ano = document.getElementById("ano");
  if (ano) ano.textContent = new Date().getFullYear();
});
