const plateInput = document.getElementById("plate");
const plateNote = document.getElementById("plate-note");
const defaultFuel = document.getElementById("fuel_type").value;
const autofillFields = [
    "customer_name", "phone", "make", "model", "year", "vin", "engine", "fuel_type",
];
let autofilled = {};

function blankValue(id) {
    return id === "fuel_type" ? defaultFuel : "";
}

function canFill(field) {
    return field.value === blankValue(field.id) || field.value === autofilled[field.id];
}

function fillFields(visit) {
    const filled = {};
    for (const id of autofillFields) {
        const field = document.getElementById(id);
        if (canFill(field)) {
            field.value = visit[id] || blankValue(id);
            filled[id] = field.value;
        }
    }
    autofilled = filled;
    fillModels();
}

async function findLastVisit(plate) {
    const params = new URLSearchParams({plate: plate});
    try {
        const response = await fetch(plateNote.dataset.url + "?" + params);
        if (response.ok && !response.redirected) {
            return await response.json();
        }
    } catch (error) {
        console.error(error);
    }
    return {};
}

async function autofillFromPlate() {
    const plate = plateInput.value;
    const visit = await findLastVisit(plate);
    if (plate !== plateInput.value) {
        return;
    }

    fillFields(visit);
    if (visit.date_received) {
        plateNote.textContent = `Filled in from the visit on ${visit.date_received}. Check the details.`;
    } else {
        plateNote.textContent = "";
    }
}

plateInput.addEventListener("change", autofillFromPlate);