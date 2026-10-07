(function () {
    "use strict";

    const LANGUAGES = {
        EN: ["English", "en"],
        FR: ["Français", "fr"],
        ES: ["Español", "es"],
        NL: ["Nederlands", "nl"],
        DE: ["Deutsch", "de"],
        PT: ["Português", "pt"],
        IT: ["Italiano", "it"],
        AR: ["العربية", "ar"],
        HI: ["हिन्दी", "hi"],
        BN: ["বাংলা", "bn"],
        UR: ["اردو", "ur"],
        ZH: ["中文", "zh-CN"],
        JA: ["日本語", "ja"],
        KO: ["한국어", "ko"],
        RU: ["Русский", "ru"],
        TR: ["Türkçe", "tr"],
        SW: ["Kiswahili", "sw"],
        PA: ["ਪੰਜਾਬੀ", "pa"],
        GU: ["ગુજરાતી", "gu"],
        ML: ["മലയാളം", "ml"]
    };

    const STORAGE_KEY = "fairmont_bank_language";
    const COOKIE_NAME = "fairmont_language";

    function getCookie(name) {
        const match = document.cookie.match(
            new RegExp("(?:^|;\\s*)" + name.replace(/[.*+?^${}()|[\\]\\\\]/g, "\\$&") + "=([^;]*)")
        );
        return match ? decodeURIComponent(match[1]) : "";
    }

    function getLanguage() {
        const stored = localStorage.getItem(STORAGE_KEY);
        if (stored && LANGUAGES[stored]) return stored;

        const cookie = getCookie(COOKIE_NAME);
        if (cookie && LANGUAGES[cookie]) return cookie;

        return "EN";
    }

    function saveLanguage(code) {
        if (!LANGUAGES[code]) return;

        localStorage.setItem(STORAGE_KEY, code);

        document.cookie =
            COOKIE_NAME + "=" + encodeURIComponent(code) +
            "; path=/; max-age=31536000; SameSite=Lax";

        const googleCode = LANGUAGES[code][1];

        if (googleCode === "en") {
            document.cookie =
                "googtrans=; path=/; max-age=0; SameSite=Lax";
        } else {
            document.cookie =
                "googtrans=/en/" + googleCode +
                "; path=/; max-age=31536000; SameSite=Lax";
        }

        // Keep the server-side preference in sync when the route exists.
        fetch("/set-language", {
            method: "POST",
            credentials: "same-origin",
            headers: {
                "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"
            },
            body: "language=" + encodeURIComponent(code)
        }).catch(function () {});
    }

    function ensureGoogleTarget() {
        let target = document.getElementById("google_translate_element");

        if (!target) {
            target = document.createElement("div");
            target.id = "google_translate_element";
            target.setAttribute("aria-hidden", "true");
            target.style.cssText =
                "position:absolute!important;left:-99999px!important;" +
                "top:-99999px!important;width:1px!important;height:1px!important;" +
                "overflow:hidden!important;";
            document.body.appendChild(target);
        }

        return target;
    }

    function initializeGoogleTranslate() {
        const target = ensureGoogleTarget();

        if (!window.google || !google.translate || !target) return;

        if (!target.querySelector(".goog-te-combo")) {
            new google.translate.TranslateElement(
                {
                    pageLanguage: "en",
                    includedLanguages: Object.keys(LANGUAGES)
                        .map(function (key) { return LANGUAGES[key][1]; })
                        .join(","),
                    autoDisplay: false
                },
                "google_translate_element"
            );
        }

        // Reapply the saved choice to the Google selector after it is created.
        const code = getLanguage();
        const googleCode = LANGUAGES[code][1];
        const combo = target.querySelector(".goog-te-combo");

        if (combo && combo.value !== googleCode) {
            combo.value = googleCode;
            combo.dispatchEvent(new Event("change"));
        }
    }

    function loadGoogleTranslate() {
        if (window.google && window.google.translate) {
            initializeGoogleTranslate();
            return;
        }

        window.googleTranslateElementInit = initializeGoogleTranslate;

        if (!document.querySelector("script[data-fairmont-google-translate]")) {
            const script = document.createElement("script");
            script.src =
                "https://translate.google.com/translate_a/element.js" +
                "?cb=googleTranslateElementInit";
            script.async = true;
            script.dataset.fairmontGoogleTranslate = "true";
            document.head.appendChild(script);
        }
    }

    function createSelector() {
        let selector =
            document.querySelector(".fairmont-global-language") ||
            document.querySelector(".language-selector") ||
            document.querySelector(".fairmont-login-language");

        if (selector) return selector;

        selector = document.createElement("div");
        selector.className = "fairmont-global-language";
        selector.innerHTML =
            '<button type="button" class="fairmont-global-language-toggle" ' +
            'aria-expanded="false" aria-haspopup="listbox">' +
            '<span class="fairmont-global-language-current">EN</span>' +
            '<span aria-hidden="true">⌄</span>' +
            '</button>' +
            '<div class="fairmont-global-language-menu" role="listbox"></div>';

        const menu =
            selector.querySelector(".fairmont-global-language-menu");

        Object.keys(LANGUAGES).forEach(function (code) {
            const button = document.createElement("button");
            button.type = "button";
            button.dataset.lang = code;
            button.setAttribute("role", "option");
            button.textContent = LANGUAGES[code][0];
            menu.appendChild(button);
        });

        document.body.appendChild(selector);
        return selector;
    }

    function bindSelector(selector) {
        if (!selector || selector.dataset.fairmontLanguageBound === "true") {
            return;
        }

        selector.dataset.fairmontLanguageBound = "true";

        const toggle =
            selector.querySelector(
                ".fairmont-global-language-toggle, .language-toggle, #fairmont-login-language-toggle"
            );

        const menu =
            selector.querySelector(
                ".fairmont-global-language-menu, .language-menu, #fairmont-login-language-menu"
            );

        const current =
            selector.querySelector(
                ".fairmont-global-language-current, .language-current, #fairmont-login-language-current"
            );

        if (!toggle || !menu || !current) return;

        const saved = getLanguage();
        current.textContent = saved;

        toggle.addEventListener("click", function (event) {
            event.preventDefault();
            event.stopPropagation();

            const open = menu.classList.toggle("open");
            toggle.setAttribute("aria-expanded", open ? "true" : "false");
        });

        menu.querySelectorAll("[data-lang]").forEach(function (item) {
            item.addEventListener("click", function () {
                const code = item.dataset.lang;
                if (!LANGUAGES[code]) return;

                current.textContent = code;
                menu.classList.remove("open");
                toggle.setAttribute("aria-expanded", "false");

                saveLanguage(code);

                // A full reload is intentional: the Google translation cookie
                // is then applied to the entire new page, including dashboard,
                // transfers, payments, profile, invoices, etc.
                window.location.reload();
            });
        });

        document.addEventListener("click", function (event) {
            if (!selector.contains(event.target)) {
                menu.classList.remove("open");
                toggle.setAttribute("aria-expanded", "false");
            }
        });
    }

    function start() {
        ensureGoogleTarget();

        const selector = createSelector();
        bindSelector(selector);
        loadGoogleTranslate();

        // Google Translate loads asynchronously, so retry initialization.
        setTimeout(initializeGoogleTranslate, 700);
        setTimeout(initializeGoogleTranslate, 1800);
        setTimeout(initializeGoogleTranslate, 3500);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", start);
    } else {
        start();
    }
})();
