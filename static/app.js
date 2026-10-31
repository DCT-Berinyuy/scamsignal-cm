// ScamSignal CM - Frontend controller
// Privacy & Security: zero client storage, zero logging of messages, all server text set via textContent.

(function () {
  "use strict";

  const STRINGS = {
    en: {
      tagline: "Check suspicious Mobile Money messages in Cameroon",
      examplesTitle: "Try an example:",
      examples: {
        "en-scam": "EN scam",
        "fr-scam": "FR scam",
        "pcm-scam": "Pidgin scam",
        "real-msg": "Real message",
        "tricky-scam": "Tricky scam",
      },
      privacyWarning: "Do not paste PINs, OTP codes or personal details.",
      pasteLabel: "Paste SMS or WhatsApp message:",
      placeholder: "Paste suspicious message here...",
      senderLegend: "Who sent it?",
      senderNamed: "Named sender (e.g. MobileMoney, OrangeMoney)",
      senderNumber: "Phone number",
      senderUnknown: "Don't know",
      checkBtn: "Check message",
      checkingBtn: "Checking...",
      reasonsHeading: "Why we think so",
      adviceHeading: "Safe next step",
      reminder: "Verify in the official app. Never share your PIN or OTP.",
      confidence: "This is a warning signal, not proof. Check in the official app.",
      err422: "Please paste a message (max 1000 characters).",
      errNetwork: "Could not check right now. Try again.",
      aboutHeading: "About & Limitations",
      aboutP1: "It's a warning signal, not proof. It never blocks anything and never contacts anyone.",
      aboutP2: "We don't store or log messages.",
      aboutP3: "The message is sent to Google's Gemini API to get the AI explanation. Phone numbers and long digit runs are replaced with [NUMBER] first. Google may use free-tier inputs to improve its products.",
      aboutP4: "Pidgin support is experimental.",
      footerText: "Built for Mobile Money safety in Cameroon.",
      labels: {
        suspicious: "Suspicious",
        unclear: "Unclear",
        no_warning_signs: "No warning signs found",
      },
    },
    fr: {
      tagline: "Vérifiez les messages Mobile Money suspects au Cameroun",
      examplesTitle: "Essayer un exemple :",
      examples: {
        "en-scam": "Arnaque EN",
        "fr-scam": "Arnaque FR",
        "pcm-scam": "Arnaque Pidgin",
        "real-msg": "Vrai message",
        "tricky-scam": "Arnaque piège",
      },
      privacyWarning: "Ne collez aucun code PIN, code OTP ou information personnelle.",
      pasteLabel: "Collez le message SMS ou WhatsApp :",
      placeholder: "Collez le message suspect ici...",
      senderLegend: "Qui l'a envoyé ?",
      senderNamed: "Expéditeur identifié (ex. MobileMoney, OrangeMoney)",
      senderNumber: "Numéro de téléphone",
      senderUnknown: "Je ne sais pas",
      checkBtn: "Vérifier le message",
      checkingBtn: "Vérification en cours...",
      reasonsHeading: "Pourquoi nous le signalons",
      adviceHeading: "Étape suivante sécurisée",
      reminder: "Vérifiez dans l'application officielle. Ne communiquez jamais votre code PIN ou OTP.",
      confidence: "Ceci est un signal d'alerte, pas une preuve. Vérifiez dans l'application officielle.",
      err422: "Veuillez coller un message (1000 caractères max).",
      errNetwork: "Impossible de vérifier pour l'instant. Réessayez.",
      aboutHeading: "À propos et limites",
      aboutP1: "C'est un signal d'avertissement, pas une preuve. Il ne bloque rien et ne contacte personne.",
      aboutP2: "Nous n'enregistrons et ne conservons aucun message.",
      aboutP3: "Le message est envoyé à l'API Gemini de Google pour obtenir l'explication de l'IA. Les numéros de téléphone et suites de chiffres sont d'abord remplacés par [NUMBER]. Google peut utiliser les entrées de l'offre gratuite pour améliorer ses produits.",
      aboutP4: "La prise en charge du Pidgin est expérimentale.",
      footerText: "Développé pour la sécurité Mobile Money au Cameroun.",
      labels: {
        suspicious: "Suspect",
        unclear: "Pas clair",
        no_warning_signs: "Aucun signal d'alerte trouvé",
      },
    },
    // needs native-speaker review (PRD §16)
    pcm: {
      tagline: "Check suspicious Mobile Money message for Cameroon",
      examplesTitle: "Try example:",
      examples: {
        "en-scam": "EN scam",
        "fr-scam": "FR scam",
        "pcm-scam": "Pidgin scam",
        "real-msg": "Real message",
        "tricky-scam": "Tricky scam",
      },
      privacyWarning: "No put your PIN, OTP code or any secret info here.",
      pasteLabel: "Paste SMS or WhatsApp message:",
      placeholder: "Paste suspicious message here...",
      senderLegend: "Na who send am?",
      senderNamed: "Name sender (e.g. MobileMoney, OrangeMoney)",
      senderNumber: "Phone number",
      senderUnknown: "I no know",
      checkBtn: "Check message",
      checkingBtn: "Di check...",
      reasonsHeading: "Why we tink so",
      adviceHeading: "Safe next step",
      reminder: "Verify for official app. No ever share your PIN or OTP.",
      confidence: "Na warning sign, no be proof. Check for official app.",
      err422: "Abeg paste message (max 1000 characters).",
      errNetwork: "We no fit check now now. Try again.",
      aboutHeading: "About & Limitations",
      aboutP1: "Na warning sign, no be proof. E no di block anything and e no di contact anybody.",
      aboutP2: "We no di keep or store messages.",
      aboutP3: "We di send message go Google Gemini API make AI explain. We di change phone number and long numbers to [NUMBER] first. Google fit use free-tier text make e improve dem product.",
      aboutP4: "Pidgin support na experiment.",
      footerText: "Built for Mobile Money safety in Cameroon.",
      labels: {
        suspicious: "Suspicious",
        unclear: "E no clear",
        no_warning_signs: "No warning signs found",
      },
    },
  };

  const EXAMPLES = {
    "en-scam": {
      text: "Congratulations! Your number won 500,000 FCFA in the MoMo promo. To receive it, confirm your PIN by sending it to 6XX XXX XXX today.",
      lang: "en",
      sender_type: "number",
    },
    "fr-scam": {
      text: "Bonjour, je vous ai envoyé 25 000 FCFA par erreur sur votre compte Orange Money. Svp renvoyez-les moi vite, c'était pour l'hôpital.",
      lang: "fr",
      sender_type: "number",
    },
    "pcm-scam": {
      text: "My broda, MTN don give you bonus of 100 000 FCFA. Send your PIN quick quick make dem credit your account.",
      lang: "pcm",
      sender_type: "number",
    },
    "real-msg": {
      text: "Transfer of 10,000 FCFA from PAUL T. received. New balance: 15,500 FCFA. Never share your PIN with anyone.",
      lang: "en",
      sender_type: "named",
    },
    "tricky-scam": {
      text: "Hi, this is your uncle on a new line. My phone fell in water. Kindly help me with something small, I will explain when I see you.",
      lang: "en",
      sender_type: "unknown",
    },
  };

  // State
  let currentLang = "en";
  let currentSenderType = "unknown";
  let isChecking = false;

  // DOM Elements
  const appTitleEl = document.getElementById("app-title");
  const appTaglineEl = document.getElementById("app-tagline");
  const langGroupEl = document.getElementById("lang-group");
  const examplesTitleEl = document.getElementById("examples-title");
  const exampleButtonsEl = document.getElementById("example-buttons");
  const privacyWarningTextEl = document.getElementById("privacy-warning-text");
  const messageLabelEl = document.getElementById("message-label");
  const messageInputEl = document.getElementById("message-input");
  const charCountEl = document.getElementById("char-count");
  const senderLegendEl = document.getElementById("sender-legend");
  const senderGroupEl = document.getElementById("sender-group");
  const senderNamedBtn = document.getElementById("sender-named");
  const senderNumberBtn = document.getElementById("sender-number");
  const senderUnknownBtn = document.getElementById("sender-unknown");
  const checkBtn = document.getElementById("check-btn");
  const errorBoxEl = document.getElementById("error-box");
  const resultCardEl = document.getElementById("result-card");
  const resultBadgeEl = document.getElementById("result-badge");
  const resultIconEl = document.getElementById("result-icon");
  const resultLabelEl = document.getElementById("result-label");
  const reasonsHeadingEl = document.getElementById("reasons-heading");
  const reasonsListEl = document.getElementById("reasons-list");
  const whyTextEl = document.getElementById("why-text");
  const adviceHeadingEl = document.getElementById("advice-heading");
  const adviceTextEl = document.getElementById("advice-text");
  const reminderTextEl = document.getElementById("reminder-text");
  const confidenceTextEl = document.getElementById("confidence-text");
  const aboutHeadingEl = document.getElementById("about-heading");
  const aboutP1El = document.getElementById("about-p1");
  const aboutP2El = document.getElementById("about-p2");
  const aboutP3El = document.getElementById("about-p3");
  const aboutP4El = document.getElementById("about-p4");
  const footerTextEl = document.getElementById("footer-text");

  function init() {
    fetchHealth();
    bindEvents();
    updateLanguage(currentLang);
    updateCharCount();
  }

  function fetchHealth() {
    fetch("/health")
      .then(function (res) {
        if (!res.ok) throw new Error("health check failed");
        return res.json();
      })
      .then(function (data) {
        if (data && data.app_name) {
          document.title = data.app_name;
          appTitleEl.textContent = data.app_name;
        }
      })
      .catch(function () {
        // Fallback default already in HTML
      });
  }

  function bindEvents() {
    // Language toggle group
    langGroupEl.addEventListener("click", function (evt) {
      const btn = evt.target.closest(".btn-toggle");
      if (!btn) return;
      const lang = btn.getAttribute("data-lang");
      if (lang && STRINGS[lang] && lang !== currentLang) {
        updateLanguage(lang);
      }
    });

    // Sender toggle group
    senderGroupEl.addEventListener("click", function (evt) {
      const btn = evt.target.closest(".btn-toggle");
      if (!btn) return;
      const sender = btn.getAttribute("data-sender");
      if (sender) {
        setSenderType(sender);
      }
    });

    // Message input input/paste/keyup
    messageInputEl.addEventListener("input", function () {
      updateCharCount();
      hideError();
    });

    // Check button click
    checkBtn.addEventListener("click", function () {
      runCheck();
    });

    // Example buttons
    exampleButtonsEl.addEventListener("click", function (evt) {
      const btn = evt.target.closest(".btn-example");
      if (!btn) return;
      const exampleId = btn.getAttribute("data-example");
      const ex = EXAMPLES[exampleId];
      if (!ex) return;

      messageInputEl.value = ex.text;
      setSenderType(ex.sender_type);
      updateLanguage(ex.lang);
      updateCharCount();
      runCheck();
    });
  }

  function updateCharCount() {
    const len = messageInputEl.value.length;
    charCountEl.textContent = len + " / 1000";
    checkBtn.disabled = len === 0 || !messageInputEl.value.trim() || isChecking;
  }

  function setSenderType(sender) {
    currentSenderType = sender;
    const buttons = senderGroupEl.querySelectorAll(".btn-toggle");
    buttons.forEach(function (b) {
      const isSelected = b.getAttribute("data-sender") === sender;
      b.classList.toggle("active", isSelected);
      b.setAttribute("aria-pressed", isSelected ? "true" : "false");
    });
  }

  function updateLanguage(lang) {
    currentLang = lang;
    const strings = STRINGS[lang] || STRINGS.en;

    // Update lang buttons
    const langButtons = langGroupEl.querySelectorAll(".btn-toggle");
    langButtons.forEach(function (b) {
      const isSelected = b.getAttribute("data-lang") === lang;
      b.classList.toggle("active", isSelected);
      b.setAttribute("aria-pressed", isSelected ? "true" : "false");
    });

    // Update fixed strings
    document.documentElement.lang = lang;
    appTaglineEl.textContent = strings.tagline;
    examplesTitleEl.textContent = strings.examplesTitle;

    // Example button labels
    for (const key in strings.examples) {
      const exBtn = document.getElementById("ex-" + key);
      if (exBtn) {
        exBtn.textContent = strings.examples[key];
      }
    }

    privacyWarningTextEl.textContent = strings.privacyWarning;
    messageLabelEl.textContent = strings.pasteLabel;
    messageInputEl.placeholder = strings.placeholder;
    senderLegendEl.textContent = strings.senderLegend;
    senderNamedBtn.textContent = strings.senderNamed;
    senderNumberBtn.textContent = strings.senderNumber;
    senderUnknownBtn.textContent = strings.senderUnknown;

    checkBtn.textContent = isChecking ? strings.checkingBtn : strings.checkBtn;
    reasonsHeadingEl.textContent = strings.reasonsHeading;
    adviceHeadingEl.textContent = strings.adviceHeading;
    reminderTextEl.textContent = strings.reminder;
    confidenceTextEl.textContent = strings.confidence;
    aboutHeadingEl.textContent = strings.aboutHeading;
    aboutP1El.textContent = strings.aboutP1;
    aboutP2El.textContent = strings.aboutP2;
    aboutP3El.textContent = strings.aboutP3;
    aboutP4El.textContent = strings.aboutP4;
    footerTextEl.textContent = strings.footerText;
  }

  function showError(msg) {
    errorBoxEl.textContent = msg;
    errorBoxEl.classList.remove("hidden");
  }

  function hideError() {
    errorBoxEl.textContent = "";
    errorBoxEl.classList.add("hidden");
  }

  function runCheck() {
    const text = messageInputEl.value.trim();
    if (!text || isChecking) return;

    isChecking = true;
    checkBtn.disabled = true;
    checkBtn.textContent = STRINGS[currentLang].checkingBtn;
    hideError();
    resultCardEl.classList.add("hidden");

    const payload = {
      text: text,
      lang: currentLang,
      sender_type: currentSenderType,
    };

    fetch("/check", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    })
      .then(function (res) {
        if (res.status === 422) {
          throw new Error("422");
        }
        if (!res.ok) {
          throw new Error("network_error");
        }
        return res.json();
      })
      .then(function (data) {
        renderResult(data);
      })
      .catch(function (err) {
        if (err.message === "422") {
          showError(STRINGS[currentLang].err422);
        } else {
          showError(STRINGS[currentLang].errNetwork);
        }
      })
      .finally(function () {
        isChecking = false;
        checkBtn.textContent = STRINGS[currentLang].checkBtn;
        updateCharCount();
      });
  }

  function renderResult(data) {
    const strings = STRINGS[currentLang] || STRINGS.en;

    // Reset badge classes
    resultBadgeEl.className = "result-badge";

    let labelText = "";
    let iconText = "";

    if (data.label === "suspicious") {
      resultBadgeEl.classList.add("badge-suspicious");
      iconText = "[\u26A0]"; // [!] warning sign
      labelText = strings.labels.suspicious;
    } else if (data.label === "unclear") {
      resultBadgeEl.classList.add("badge-unclear");
      iconText = "[?]";
      labelText = strings.labels.unclear;
    } else {
      // no_warning_signs - strictly NEUTRAL GREY, never green
      resultBadgeEl.classList.add("badge-no-warning");
      iconText = "[-]";
      labelText = strings.labels.no_warning_signs;
    }

    resultIconEl.textContent = iconText;
    resultLabelEl.textContent = labelText;

    // Reasons list: build via textContent
    while (reasonsListEl.firstChild) {
      reasonsListEl.removeChild(reasonsListEl.firstChild);
    }

    if (Array.isArray(data.reasons) && data.reasons.length > 0) {
      data.reasons.forEach(function (reason) {
        const li = document.createElement("li");
        li.textContent = reason;
        reasonsListEl.appendChild(li);
      });
    }

    // Why text
    whyTextEl.textContent = data.why || "";

    // Advice text
    adviceTextEl.textContent = data.advice || "";

    // Show result card
    resultCardEl.classList.remove("hidden");
    resultCardEl.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  // Initialize once DOM is ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
