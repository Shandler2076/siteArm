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

  /* Liste déroulante avec recherche (demande du 20/11/2026) : on ne fouille jamais une longue
     liste (paroisses…) ; on tape quelques lettres, sans souci des accents. Toute liste marquée
     data-recherche, et en filet de sécurité toute liste de plus de SEUIL_RECHERCHE choix. La
     vraie liste reste dans la page (envoi du formulaire, cascade région → circuit → paroisse). */
  var SEUIL_RECHERCHE = 15;
  var MAX_PROPOSITIONS = 80;

  function sansAccents(t) {
    return t.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  }

  function listeAvecRecherche(select) {
    if (select.dataset.rechercheActive || select.multiple || select.size > 1) return;
    select.dataset.rechercheActive = "1";
    var bloc = document.createElement("span");
    bloc.className = "choix-recherche";
    select.parentNode.insertBefore(bloc, select);
    var saisie = document.createElement("input");
    saisie.type = "text";
    saisie.className = "choix-recherche__saisie";
    saisie.placeholder = "Tapez quelques lettres pour rechercher…";
    saisie.autocomplete = "off";
    saisie.setAttribute("role", "combobox");
    saisie.setAttribute("aria-expanded", "false");
    saisie.setAttribute("aria-autocomplete", "list");
    var etiquette = select.closest("label");
    var titre = etiquette && etiquette.querySelector("span");
    saisie.setAttribute("aria-label", "Rechercher " + (titre ? titre.textContent.trim().toLowerCase() : "dans la liste"));
    var resultats = document.createElement("ul");
    resultats.className = "choix-recherche__resultats";
    resultats.setAttribute("role", "listbox");
    resultats.hidden = true;
    bloc.appendChild(saisie);
    bloc.appendChild(resultats);
    bloc.appendChild(select);
    select.tabIndex = -1;
    select.setAttribute("aria-hidden", "true");
    var actif = -1;

    function texteChoisi() {
      var o = select.options[select.selectedIndex];
      return o && o.value ? o.textContent.trim() : "";
    }
    function majTexte() { saisie.value = texteChoisi(); }
    function fermer() {
      resultats.hidden = true;
      saisie.setAttribute("aria-expanded", "false");
      actif = -1;
    }
    function choisir(o) {
      select.value = o.value;
      saisie.value = o.value ? o.textContent.trim() : "";
      fermer();
      select.dispatchEvent(new Event("change", { bubbles: true }));
    }
    function surligner(i) {
      var lignes = resultats.querySelectorAll("li[data-i]");
      if (!lignes.length) return;
      actif = (i + lignes.length) % lignes.length;
      lignes.forEach(function (l, k) { l.classList.toggle("actif", k === actif); });
      lignes[actif].scrollIntoView({ block: "nearest" });
    }
    function proposer(texte) {
      var mots = sansAccents(texte.trim()).split(/\s+/).filter(Boolean);
      resultats.replaceChildren();
      var total = 0;
      Array.prototype.forEach.call(select.options, function (o, i) {
        if (o.disabled || o.hidden) return;
        if (!o.value && (select.required || mots.length)) return;
        var lib = sansAccents(o.textContent);
        if (!mots.every(function (m) { return lib.indexOf(m) !== -1; })) return;
        total += 1;
        if (total > MAX_PROPOSITIONS) return;
        var li = document.createElement("li");
        li.setAttribute("role", "option");
        li.dataset.i = i;
        li.textContent = o.value ? o.textContent.trim() : "— Aucun choix —";
        resultats.appendChild(li);
      });
      if (!total) {
        var rien = document.createElement("li");
        rien.className = "info";
        rien.textContent = "Aucun résultat : vérifiez l'orthographe.";
        resultats.appendChild(rien);
      } else if (total > MAX_PROPOSITIONS) {
        var info = document.createElement("li");
        info.className = "info";
        info.textContent = total + " résultats : tapez quelques lettres de plus pour affiner.";
        resultats.appendChild(info);
      }
      resultats.hidden = false;
      saisie.setAttribute("aria-expanded", "true");
      actif = -1;
    }

    saisie.addEventListener("focus", function () { saisie.select(); proposer(""); });
    saisie.addEventListener("input", function () { proposer(saisie.value); });
    saisie.addEventListener("keydown", function (e) {
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault();
        if (resultats.hidden) proposer(saisie.value);
        surligner(actif + (e.key === "ArrowDown" ? 1 : -1));
      } else if (e.key === "Enter" && !resultats.hidden) {
        e.preventDefault();  // jamais d'envoi du formulaire par erreur
        var lignes = resultats.querySelectorAll("li[data-i]");
        var l = lignes[actif >= 0 ? actif : 0];
        if (l && (actif >= 0 || lignes.length === 1)) choisir(select.options[l.dataset.i]);
      } else if (e.key === "Escape") {
        fermer();
        majTexte();
      }
    });
    saisie.addEventListener("blur", function () {
      setTimeout(function () {
        if (document.activeElement === saisie) return;
        fermer();
        if (!saisie.value.trim() && !select.required && select.value) {
          choisir({ value: "", textContent: "" });
        } else {
          majTexte();
        }
      }, 150);
    });
    // mousedown : la saisie garde la main ; click : pas d'activation de l'étiquette.
    resultats.addEventListener("mousedown", function (e) { e.preventDefault(); });
    resultats.addEventListener("click", function (e) {
      e.preventDefault();
      var li = e.target.closest("li[data-i]");
      if (li) choisir(select.options[li.dataset.i]);
    });
    // La cascade (région → circuit → paroisse) peut vider le choix : on suit.
    if (select.form) select.form.addEventListener("change", function () {
      if (document.activeElement !== saisie) majTexte();
    });
    select.addEventListener("invalid", function () { saisie.focus(); });
    majTexte();
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
    document.querySelectorAll("select[data-recherche]").forEach(listeAvecRecherche);
    document.querySelectorAll("select:not([multiple])").forEach(function (s) {
      if (s.options.length > SEUIL_RECHERCHE) listeAvecRecherche(s);
    });
  });
})();
