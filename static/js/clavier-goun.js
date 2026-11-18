/* Clavier goun : lettres spéciales et mots proposés, pour les champs marqués data-clavier.
   Les lettres et les mots viennent du site (liste du Bureau national + mots déjà écrits).
   Rien n'est envoyé ailleurs. */
(function () {
  "use strict";

  var LETTRE = /[\p{L}\p{M}'’-]+$/u;

  function sansAccents(t) {
    return t.normalize("NFD").replace(/\p{M}/gu, "").toLowerCase();
  }

  function initialiser(panneau) {
    var donnees = JSON.parse(document.getElementById(panneau.dataset.source).textContent);
    var lettresZone = panneau.querySelector(".clavier__lettres");
    var motsZone = panneau.querySelector(".clavier__mots");
    var champs = document.querySelectorAll("[data-clavier]");
    var cible = champs[0] || null;
    var majuscule = false;
    var urlMots = panneau.dataset.mots, cache = {}, attente = null, demande = 0;

    function bouton(texte, classe, action, etiquette) {
      var b = document.createElement("button");
      b.type = "button";
      b.className = classe;
      b.textContent = texte;
      if (etiquette) b.setAttribute("aria-label", etiquette);
      // Garder le curseur dans le champ : pas de perte de focus au clic.
      b.addEventListener("mousedown", function (e) { e.preventDefault(); });
      b.addEventListener("click", action);
      return b;
    }

    function inserer(texte, remplacer) {
      if (!cible) return;
      var debut = cible.selectionStart, fin = cible.selectionEnd;
      if (remplacer) debut -= remplacer;
      cible.setRangeText(texte, debut, fin, "end");
      cible.focus();
      cible.dispatchEvent(new Event("input", { bubbles: true }));
    }

    var TONS = {
      "\u0301": ["´", "Ton haut"],
      "\u0300": ["`", "Ton bas"],
      "\u0303": ["~", "Nasale"],
      "\u0302": ["^", "Accent circonflexe"],
      "\u0304": ["¯", "Ton moyen"],
      "\u030C": ["ˇ", "Ton montant"]
    };

    /* Un ton se pose sur la lettre qui précède le curseur (ẹ + ´ → ẹ́). */
    function poserTon(marque) {
      if (!cible) return;
      var pos = cible.selectionStart;
      var avant = (cible.value.slice(0, pos) + marque).normalize("NFC");
      cible.value = avant + cible.value.slice(cible.selectionEnd);
      cible.selectionStart = cible.selectionEnd = avant.length;
      cible.focus();
      cible.dispatchEvent(new Event("input", { bubbles: true }));
    }

    function dessinerLettres() {
      lettresZone.innerHTML = "";
      donnees.lettres.forEach(function (l) {
        if (l.charAt(0) === "\u25CC") {
          var marque = l.slice(1), ton = TONS[marque] || [l, "Ton"];
          var b = bouton(ton[0], "clavier__touche clavier__touche--ton", function () { poserTon(marque); }, ton[1]);
          b.title = ton[1] + " : sur la lettre déjà tapée";
          lettresZone.appendChild(b);
          return;
        }
        var t = majuscule ? l.toUpperCase() : l;
        lettresZone.appendChild(bouton(t, "clavier__touche", function () { inserer(t); }, "Lettre " + t));
      });
      var maj = bouton("⇧ Maj", "clavier__touche clavier__touche--large" + (majuscule ? " actif" : ""), function () {
        majuscule = !majuscule;
        dessinerLettres();
      }, "Majuscules");
      maj.setAttribute("aria-pressed", majuscule ? "true" : "false");
      lettresZone.appendChild(maj);
    }

    function motEnCours() {
      if (!cible) return "";
      var avant = cible.value.slice(0, cible.selectionStart);
      var m = avant.match(LETTRE);
      return m ? m[0] : "";
    }

    function afficher(debut, mots) {
      motsZone.textContent = "";
      mots.forEach(function (m) {
        var mot = m;
        if (debut && debut[0] !== debut[0].toLowerCase()) mot = m[0].toUpperCase() + m.slice(1);
        motsZone.appendChild(bouton(mot, "clavier__mot", function () { inserer(mot + " ", debut.length); }));
      });
      motsZone.hidden = mots.length === 0;
    }

    /* Mots proposés : demandés au site au fil de la frappe (lexique goun, liste du BN, mots appris). */
    function proposer() {
      var debut = motEnCours();
      var cle = sansAccents(debut);
      clearTimeout(attente);
      if (!cle || !urlMots) { afficher("", []); return; }
      if (cache[debut]) { afficher(debut, cache[debut]); return; }
      var numero = ++demande;
      attente = setTimeout(function () {
        fetch(urlMots + "?debut=" + encodeURIComponent(debut), { credentials: "same-origin" })
          .then(function (r) { return r.ok ? r.json() : { mots: [] }; })
          .then(function (d) {
            cache[debut] = d.mots || [];
            if (numero === demande) afficher(debut, cache[debut]);
          })
          .catch(function () {});
      }, 150);
    }

    Array.prototype.forEach.call(champs, function (c) {
      c.addEventListener("focus", function () { cible = c; proposer(); });
      c.addEventListener("input", proposer);
      c.addEventListener("click", proposer);
      c.addEventListener("keyup", function (e) {
        if (e.key && e.key.indexOf("Arrow") === 0) proposer();
      });
    });
    dessinerLettres();
    proposer();
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".clavier[data-source]").forEach(initialiser);
  });
})();
