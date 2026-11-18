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
    var index = donnees.mots.map(function (m) { return [sansAccents(m), m]; });

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

    function proposer() {
      motsZone.innerHTML = "";
      var debut = motEnCours();
      var cle = sansAccents(debut);
      var vus = 0;
      for (var i = 0; i < index.length && vus < 8; i++) {
        var paire = index[i];
        if (cle && (paire[0].indexOf(cle) !== 0 || paire[1] === debut.toLowerCase())) continue;
        var mot = paire[1];
        if (debut && debut[0] !== debut[0].toLowerCase()) mot = mot[0].toUpperCase() + mot.slice(1);
        (function (m, longueur) {
          motsZone.appendChild(bouton(m, "clavier__mot", function () { inserer(m + " ", longueur); }));
        })(mot, debut.length);
        vus++;
      }
      motsZone.hidden = vus === 0;
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
