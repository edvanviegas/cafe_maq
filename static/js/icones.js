/* Ícones de traço sem cor. Os desenhos ficam em templates/_icones.html (incluído no base.html).
   Uso: icone("trator")  ->  '<svg class="ic">...</svg>' */
function icone(nome) {
  return '<svg class="ic" aria-hidden="true"><use href="#ic-' + nome + '"></use></svg>';
}
