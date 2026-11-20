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

  /* Gestes de l'interface sans JavaScript écrit dans les pages (exigé par la politique de
     sécurité des contenus, CSP) : chaque élément les déclare par un attribut data-… */
  document.addEventListener("submit", function (e) {
    var f = e.target;
    if (f.dataset && f.dataset.confirmer && !window.confirm(f.dataset.confirmer)) e.preventDefault();
  }, true);
  document.addEventListener("click", function (e) {
    var el = e.target.closest ? e.target.closest("[data-confirmer], [data-action]") : null;
    if (!el || el.tagName === "FORM") return;
    if (el.dataset.confirmer && !window.confirm(el.dataset.confirmer)) { e.preventDefault(); return; }
    switch (el.dataset.action) {
      case "menu":
        el.setAttribute("aria-expanded", document.body.classList.toggle("menu-ouvert"));
        break;
      case "fermer-menu":
        document.body.classList.remove("menu-ouvert");
        break;
      case "retour":
        if (document.referrer.indexOf(location.host) !== -1 && history.length > 1) {
          e.preventDefault();
          history.back();
        }
        break;
      case "retirer-ligne":
        el.parentNode.remove();
        break;
      case "copier":
        navigator.clipboard.writeText(el.dataset.texte).then(
          function () { el.textContent = "Clé copiée ✓"; },
          function () { el.textContent = "Copie impossible : recopiez la clé ci-dessous"; }
        );
        break;
      case "tout-cocher":
        document.querySelectorAll('input[name="' + el.dataset.cases + '"]').forEach(function (c) {
          c.checked = el.checked;
        });
        break;
    }
  });
  document.addEventListener("change", function (e) {
    if (e.target.dataset && "soumettreAuto" in e.target.dataset && e.target.form) e.target.form.submit();
  });

  var calme = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* 2. Compteurs : le chiffre monte de 0 à sa valeur (environ 0,8 seconde). */
  function compter(el) {
    var texte = el.textContent.trim();
    if (!/^\d[\d\s\u202f\u00a0]*$/.test(texte)) return;
    var fin = parseInt(texte.replace(/\D/g, ""), 10);
    if (!fin || calme) return;
    var debut = null, duree = Math.min(1200, 500 + fin * 15);
    function format(n) { return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, "\u202f"); }
    function pas(t) {
      if (debut === null) debut = t;
      var p = Math.min(1, (t - debut) / duree), e = 1 - Math.pow(1 - p, 3);
      el.textContent = format(Math.round(fin * e));
      if (p < 1) requestAnimationFrame(pas); else el.textContent = texte;
    }
    el.textContent = "0";
    requestAnimationFrame(pas);
  }

  /* 4. Diaporama : une photo toutes les 5 secondes, points pour choisir. */
  function diaporama(bloc) {
    var images = bloc.querySelectorAll("img"), points = bloc.querySelector(".diaporama__points");
    if (images.length < 2) { if (images[0]) images[0].classList.add("visible"); return; }
    var i = 0, minuteur;
    var boutons = Array.prototype.map.call(images, function (img, n) {
      var b = document.createElement("button");
      b.type = "button";
      b.setAttribute("aria-label", "Photo " + (n + 1));
      b.addEventListener("click", function () { montrer(n); relancer(); });
      points.appendChild(b);
      return b;
    });
    function montrer(n) {
      images[i].classList.remove("visible"); boutons[i].classList.remove("actif");
      i = n;
      images[i].classList.add("visible"); boutons[i].classList.add("actif");
    }
    function relancer() {
      clearInterval(minuteur);
      if (!calme) minuteur = setInterval(function () { montrer((i + 1) % images.length); }, 5000);
    }
    montrer(0);
    relancer();
  }

  /* 8. Attente visible : un petit bandeau pendant la préparation d'un PDF ou d'un envoi. */
  var bandeau = null;
  function attendre(message) {
    if (!bandeau) {
      bandeau = document.createElement("div");
      bandeau.className = "attente";
      bandeau.setAttribute("role", "status");
      document.body.appendChild(bandeau);
    }
    bandeau.textContent = message;
    bandeau.hidden = false;
    clearTimeout(bandeau.minuteur);
    bandeau.minuteur = setTimeout(function () { bandeau.hidden = true; }, 6000);
  }
  window.addEventListener("pageshow", function () { if (bandeau) bandeau.hidden = true; });
  document.addEventListener("click", function (e) {
    var a = e.target.closest ? e.target.closest("a[href]") : null;
    if (a && /\.pdf(\?|$)/.test(a.getAttribute("href"))) attendre("Préparation du PDF…");
  });
  document.addEventListener("submit", function (e) {
    if (!e.defaultPrevented && e.target.method && e.target.method.toLowerCase() === "post") {
      attendre(e.target.dataset.attente || "Envoi en cours…");
    }
  });

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".tuile__valeur, .vitrine-chiffres strong, .stat .nombre, .resultat__nombre").forEach(compter);
    document.querySelectorAll(".diaporama").forEach(diaporama);
    document.querySelectorAll('input[type="password"]').forEach(voirMotDePasse);
    document.querySelectorAll("form").forEach(cascade);
    document.querySelectorAll(".deroulant").forEach(deroulant);
    document.querySelectorAll("input[data-filtre]").forEach(filtreListe);
  });
})();
