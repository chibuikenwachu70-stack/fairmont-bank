
function selectTransferType(type) {

    const hiddenType = document.getElementById("transfer_type");

    const ukFields = document.getElementById("ukFields");
    const fairmontFields = document.getElementById("fairmontFields");

    const buttons = document.querySelectorAll(".transfer-type");

    if (hiddenType) {
        hiddenType.value = type;
    }

    buttons.forEach(function(button) {

        if (button.dataset.type === type) {
            button.classList.add("active");
        } else {
            button.classList.remove("active");
        }

    });

    if (type === "fairmont") {

        if (ukFields) {
            ukFields.classList.add("hidden");
        }

        if (fairmontFields) {
            fairmontFields.classList.remove("hidden");
        }

        document
            .getElementById("recipient_name")
            ?.removeAttribute("required");

        document
            .getElementById("bank_name")
            ?.removeAttribute("required");

        document
            .getElementById("sort_code")
            ?.removeAttribute("required");

        document
            .getElementById("account_number")
            ?.removeAttribute("required");

        document
            .getElementById("fairmont_account_number")
            ?.setAttribute("required", "required");

        document
            .getElementById("fairmont_recipient_name")
            ?.setAttribute("required", "required");

    } else {

        if (fairmontFields) {
            fairmontFields.classList.add("hidden");
        }

        if (ukFields) {
            ukFields.classList.remove("hidden");
        }

        document
            .getElementById("fairmont_account_number")
            ?.removeAttribute("required");

        document
            .getElementById("fairmont_recipient_name")
            ?.removeAttribute("required");

        document
            .getElementById("recipient_name")
            ?.setAttribute("required", "required");

        document
            .getElementById("bank_name")
            ?.setAttribute("required", "required");

        document
            .getElementById("sort_code")
            ?.setAttribute("required", "required");

        document
            .getElementById("account_number")
            ?.setAttribute("required", "required");
    }
}


document.addEventListener("DOMContentLoaded", function() {

    if (document.getElementById("sendMoneyForm")) {
        selectTransferType("uk");
    }

});


/* FAIRMOnt_TRANSFER_QUICK_SEARCH_V1 */

/*
    Fairmont Bank
    Transfer Quick Search
*/

(function () {
    "use strict";

    function setupSearchableSelect(searchId, selectId, resultsId) {
        const search = document.getElementById(searchId);
        const select = document.getElementById(selectId);
        const results = document.getElementById(resultsId);

        if (!search || !select || !results) {
            return null;
        }

        function getOptions() {
            return Array.from(select.options).filter(
                option => option.value && option.textContent.trim()
            );
        }

        function renderResults() {
            const query = search.value.trim().toLowerCase();
            const options = getOptions();

            results.innerHTML = "";

            if (select.disabled) {
                results.style.display = "none";
                return;
            }

            const filtered = options.filter(option => {
                const text = option.textContent.toLowerCase();
                const value = option.value.toLowerCase();

                return !query ||
                    text.includes(query) ||
                    value.includes(query);
            });

            if (!filtered.length) {
                const empty = document.createElement("div");
                empty.className = "quick-search-empty";
                empty.textContent = "No matching options found";
                results.appendChild(empty);
                results.style.display = "block";
                return;
            }

            filtered.slice(0, 12).forEach(option => {
                const item = document.createElement("button");

                item.type = "button";
                item.className = "quick-search-option";
                item.textContent = option.textContent.trim();

                item.addEventListener("click", function () {
                    select.value = option.value;

                    search.value = option.textContent.trim();

                    results.innerHTML = "";
                    results.style.display = "none";

                    select.dispatchEvent(
                        new Event("change", { bubbles: true })
                    );
                });

                results.appendChild(item);
            });

            results.style.display = "block";
        }

        search.addEventListener("focus", renderResults);
        search.addEventListener("input", renderResults);

        select.addEventListener("change", function () {
            const selected = select.options[select.selectedIndex];

            if (selected && selected.value) {
                search.value = selected.textContent.trim();
            }
        });

        document.addEventListener("click", function (event) {
            if (
                !event.target.closest(".quick-search-select") ||
                event.target === select
            ) {
                results.style.display = "none";
            }
        });

        return {
            search,
            select,
            results,
            renderResults
        };
    }


    /*
        UK BANK
    */

    setupSearchableSelect(
        "ukBankSearch",
        "ukBank",
        "ukBankSearchResults"
    );


    /*
        INTERNATIONAL COUNTRY
    */

    const countrySearch = setupSearchableSelect(
        "countrySearch",
        "internationalCountry",
        "countrySearchResults"
    );


    /*
        INTERNATIONAL BANK
    */

    const bankSearch = setupSearchableSelect(
        "internationalBankSearch",
        "internationalBank",
        "internationalBankSearchResults"
    );


    /*
        INTERNATIONAL CURRENCY
    */

    setupSearchableSelect(
        "currencySearch",
        "internationalCurrency",
        "currencySearchResults"
    );


    /*
        COUNTRY -> BANK
        Rebuild the searchable bank selector
        whenever the country changes.
    */

    const countrySelect = document.getElementById("internationalCountry");
    const internationalBank = document.getElementById("internationalBank");
    const internationalBankSearch =
        document.getElementById("internationalBankSearch");

    if (countrySelect && internationalBank) {

        countrySelect.addEventListener("change", function () {

            const selectedCountry = this.value;

            if (!selectedCountry) {
                internationalBank.disabled = true;

                if (internationalBankSearch) {
                    internationalBankSearch.disabled = true;
                    internationalBankSearch.value = "";
                    internationalBankSearch.placeholder =
                        "Select country first...";
                }

                return;
            }

            internationalBank.disabled = false;

            if (internationalBankSearch) {
                internationalBankSearch.disabled = false;
                internationalBankSearch.value = "";
                internationalBankSearch.placeholder =
                    "Search bank...";
            }

            /*
                Allow the existing country-bank system
                to rebuild the bank options.
            */

            setTimeout(function () {

                if (internationalBankSearch) {
                    internationalBankSearch.value = "";
                }

                const event = new Event(
                    "internationalBanksUpdated"
                );

                internationalBank.dispatchEvent(event);

            }, 50);
        });
    }

})();
