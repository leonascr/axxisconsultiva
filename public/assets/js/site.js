// Comportamentos do site (substitui o JS do construtor antigo)

// Imagens de fundo das seções só carregam quando a seção se aproxima da tela
(function () {
  var sections = document.querySelectorAll('.ax-con.ax-parent:not(.ax-lazyloaded)');
  if (!('IntersectionObserver' in window)) {
    sections.forEach(function (s) { s.classList.add('ax-lazyloaded'); });
    return;
  }
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (e.isIntersecting) {
        e.target.classList.add('ax-lazyloaded');
        io.unobserve(e.target);
      }
    });
  }, { rootMargin: '200px 0px' });
  sections.forEach(function (s) { io.observe(s); });
})();

// Vídeos de fundo: só baixam quando visíveis (no celular ficam ocultos)
document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('video[data-src]').forEach(function (v) {
    if (v.offsetParent === null) return;
    v.src = v.dataset.src;
    var p = v.play();
    if (p && p.catch) p.catch(function () {});
  });
});
