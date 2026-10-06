(function () {
    "use strict";

    const LANGUAGES = [
        ["EN", "English"],
        ["FR", "Français"],
        ["ES", "Español"],
        ["NL", "Nederlands"],
        ["DE", "Deutsch"],
        ["PT", "Português"],
        ["IT", "Italiano"],
        ["AR", "العربية"],
        ["HI", "हिन्दी (India)"],
        ["BN", "বাংলা"],
        ["UR", "اردو"],
        ["ZH", "中文"],
        ["JA", "日本語"],
        ["KO", "한국어"],
        ["RU", "Русский"],
        ["TR", "Türkçe"],
        ["SW", "Kiswahili"],
        ["PA", "ਪੰਜਾਬੀ"],
        ["GU", "ગુજરાતી"],
        ["ML", "മലയാളം"]
    ];

    const GOOGLE_CODES = {
        EN: "en", FR: "fr", ES: "es", NL: "nl", DE: "de",
        PT: "pt", IT: "it", AR: "ar", HI: "hi", BN: "bn",
        UR: "ur", ZH: "zh-CN", JA: "ja", KO: "ko", RU: "ru",
        TR: "tr", SW: "sw", PA: "pa", GU: "gu", ML: "ml"
    };

    const STORAGE_KEY = "fairmont_site_language";

    function currentLanguage() {
        const saved = localStorage.getItem(STORAGE_KEY);
        return LANGUAGES.some(item => item[0] === saved) ? saved : "EN";
    }

    function setGoogleCookie(code) {
        if (code === "EN") {
            document.cookie = "googtrans=; Max-Age=0; path=/";
            return;
        }

        const googleCode = GOOGLE_CODES[code];
        if (!googleCode) return;

        const value = "/en/" + googleCode;
        document.cookie = "googtrans=" + value + "; path=/; SameSite=Lax";
    }

    function setServerLanguage(code) {
        const body = new URLSearchParams();
        body.set("language", code);

        return fetch("/set-language", {
            method: "POST",
            headers: {
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "X-Requested-With": "XMLHttpRequest"
            },
            body: body.toString(),
            credentials: "same-origin"
        }).catch(function () {
            // The browser-side preference still works if the request fails.
        });
    }

    function buildSelector() {
        let selector = document.querySelector(".language-selector");

        if (selector) {
            return selector;
        }

        selector = document.createElement("div");
        selector.className = "language-selector language-selector-global";
        selector.innerHTML = `
            <button class="language-toggle" type="button"
                    aria-expanded="false" aria-haspopup="listbox"
                    aria-label="Select language">
                <span class="language-current">EN</span>
                <span class="language-arrow">⌄</span>
            </button>
            <div class="language-menu" role="listbox"></div>
        `;

        const menu = selector.querySelector(".language-menu");

        LANGUAGES.forEach(function (item) {
            const button = document.createElement("button");
            button.type = "button";
            button.dataset.lang = item[0];
            button.textContent = item[1];
            button.setAttribute("role", "option");
            menu.appendChild(button);
        });

        document.body.appendChild(selector);
        return selector;
    }

    function bindSelector(selector) {
        if (selector.dataset.languageBound === "true") return;
        selector.dataset.languageBound = "true";

        const toggle = selector.querySelector(".language-toggle");
        const menu = selector.querySelector(".language-menu");
        const current = selector.querySelector(".language-current");

        if (!toggle || !menu || !current) return;

        current.textContent = currentLanguage();

        toggle.addEventListener("click", function (event) {
            event.stopPropagation();
            const open = menu.classList.toggle("open");
            toggle.setAttribute("aria-expanded", open ? "true" : "false");
        });

        menu.querySelectorAll("button[data-lang]").forEach(function (button) {
            button.addEventListener("click", function (event) {
                event.stopPropagation();

                const code = button.dataset.lang;
                localStorage.setItem(STORAGE_KEY, code);
                current.textContent = code;
                menu.classList.remove("open");
                toggle.setAttribute("aria-expanded", "false");

                setGoogleCookie(code);

                setServerLanguage(code).finally(function () {
                    // Reload so the Google translator starts the new page
                    // in the selected language and keeps that choice on
                    // every customer page.
                    window.location.reload();
                });
            });
        });

        document.addEventListener("click", function (event) {
            if (!selector.contains(event.target)) {
                menu.classList.remove("open");
                toggle.setAttribute("aria-expanded", "false");
            }
        });
    }

    window.googleTranslateElementInit = function () {
        if (!window.google || !google.translate) return;

        new google.translate.TranslateElement({
            pageLanguage: "en",
            autoDisplay: false,
            includedLanguages: "fr,es,nl,de,pt,it,ar,hi,bn,ur,zh-CN,ja,ko,ru,tr,sw,pa,gu,ml",
            layout: google.translate.TranslateElement.InlineLayout.SIMPLE
        }, "google_translate_element");

        const code = currentLanguage();
        if (code !== "EN") {
            const googleCode = GOOGLE_CODES[code];

            // Give the Google widget a moment to create its select, then
            // explicitly select the stored language as a fallback.
            let attempts = 0;
            const choose = function () {
                const select = document.querySelector(".goog-te-combo");
                if (select && googleCode) {
                    select.value = googleCode;
                    select.dispatchEvent(new Event("change", { bubbles: true }));
                    return;
                }
                if (attempts++ < 25) setTimeout(choose, 200);
            };
            choose();
        }
    };

    function loadGoogleTranslate() {
        if (document.getElementById("fairmont-google-translate-script")) return;

        const script = document.createElement("script");
        script.id = "fairmont-google-translate-script";
        script.src = "https://translate.google.com/translate_a/element.js?cb=googleTranslateElementInit";
        script.async = true;
        document.head.appendChild(script);
    }

    function initialize() {
        const selector = buildSelector();
        bindSelector(selector);

        const code = currentLanguage();
        setGoogleCookie(code);

        loadGoogleTranslate();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initialize);
    } else {
        initialize();
    }
})();
