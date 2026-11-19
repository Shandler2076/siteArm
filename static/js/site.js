/* Petits comportements de l'interface (aucune donnée n'est envoyée ailleurs). */
(function () {
  "use strict";

  /* Région → Circuit → Paroisse en cascade : seules les unités rattachées restent proposées. */
  function cascade(form) {
    var region = form.querySelector('select[name="region"]');
    var circuit = form.querySelector('select[name="circuit"]');
    var paroisse = form.querySelector('select[name="paroisse"]');
    function filtrer(select, garder) {
      if (!select) return;
      Array.prototype.forEach.call(select.options, function (o) {
        var visible = !o.value || garder(o);
        o.hidden = !visible;
        o.disabled = !visible;
        if (!visible && o.selected) select.value = "";
      });
    }
    function appliquer() {
      var r = region ? region.value : "";
      filtrer(circuit, function (o) { return !r || o.dataset.region === r; });
      var c = circuit ? circuit.value : "";
      filtrer(paroisse, function (o) {
        return (!r || o.dataset.region === r) && (!c || o.dataset.circuit === c);
      });
    }
    if (region) region.addEventListener("change", appliquer);
    if (circuit) circuit.addEventListener("change", appliquer);
    appliquer();
  }

  /* Listes déroulantes à cases : le titre résume les choix (« Grade : Capitaine, Major »). */
  function deroulant(d) {
    var resume = d.querySelector(".deroulant__choix");
    function maj() {
      var choix = Array.prototype.map.call(d.querySelectorAll("input:checked"), function (c) {
        return c.parentNode.textContent.trim();
      });
      resume.textContent = choix.length ? choix.join(", ") : "Tous";
    }
    d.addEventListener("change", maj);
    maj();
  }

  /* Recherche dans une longue liste à cocher. */
  function filtreListe(champ) {
    var cible = document.getElementById(champ.dataset.filtre);
    if (!cible) return;
    champ.addEventListener("input", function () {
      var t = champ.value.trim().toLowerCase();
      if (cible.tagName === "SELECT") {
        Array.prototype.forEach.call(cible.options, function (o) {
          if (!o.value || o.disabled) return;
          o.hidden = t && o.textContent.toLowerCase().indexOf(t) === -1;
        });
        return;
      }
      cible.querySelectorAll("label").forEach(function (l) {
        var ligne = l.closest("div") || l;
        ligne.hidden = t && l.textContent.toLowerCase().indexOf(t) === -1;
      });
    });
  }

  /* « Voir » à côté de chaque mot de passe (décision du 19/11/2026). */
  function voirMotDePasse(champ) {
    if (champ.dataset.voir) return;
    champ.dataset.voir = "1";
    var enveloppe = document.createElement("span");
    enveloppe.className = "mot-de-passe";
    champ.parentNode.insertBefore(enveloppe, champ);
    enveloppe.appendChild(champ);
    var bouton = document.createElement("button");
    bouton.type = "button";
    bouton.className = "voir-mdp";
    bouton.textContent = "Voir";
    bouton.setAttribute("aria-label", "Afficher le mot de passe");
    bouton.addEventListener("click", function () {
      var cache = champ.type === "password";
      champ.type = cache ? "text" : "password";
      bouton.textContent = cache ? "Cacher" : "Voir";
      bouton.setAttribute("aria-label", cache ? "Cacher le mot de passe" : "Afficher le mot de passe");
      champ.focus();
    });
    enveloppe.appendChild(bouton);
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll('input[type="password"]').forEach(voirMotDePasse);
    document.querySelectorAll("form").forEach(cascade);
    document.querySelectorAll(".deroulant").forEach(deroulant);
    document.querySelectorAll("input[data-filtre]").forEach(filtreListe);
  });
})();
