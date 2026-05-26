const dropZone = document.getElementById("dropZone");
const fileInput = document.getElementById("fileInput");
const progress = document.getElementById("progress");
const result = document.getElementById("result");
const error = document.getElementById("error");

let currentFilename = "";

dropZone.addEventListener("click", () => fileInput.click());
dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("drag-over");
});
dropZone.addEventListener("dragleave", () => dropZone.classList.remove("drag-over"));
dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("drag-over");
    const files = e.dataTransfer.files;
    if (files.length > 0) handleFile(files[0]);
});

fileInput.addEventListener("change", () => {
    if (fileInput.files.length > 0) handleFile(fileInput.files[0]);
});

async function handleFile(file) {
    hideResult();
    hideError();
    showProgress();

    const formData = new FormData();
    formData.append("file", file);

    try {
        const resp = await fetch("/upload", { method: "POST", body: formData });
        const data = await resp.json();
        hideProgress();

        if (!data.ok) {
            showError(data.error);
            return;
        }

        currentFilename = data.filename;
        showResult(data);
    } catch (err) {
        hideProgress();
        showError("上传或处理失败: " + err.message);
    }
}

document.getElementById("downloadBtn").addEventListener("click", async () => {
    try {
        const resp = await fetch("/download", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ filename: currentFilename }),
        });
        if (!resp.ok) throw new Error("下载失败");

        const blob = await resp.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "processed_" + currentFilename.replace(/\.[^.]+$/, ".xlsx");
        a.click();
        URL.revokeObjectURL(url);
    } catch (err) {
        showError("下载失败: " + err.message);
    }
});

function showResult(data) {
    document.getElementById("fileInfo").textContent = data.filename + " (" + data.rows + " 行)";

    document.getElementById("stats").innerHTML = `
        <div class="stat-card"><div class="number">${data.rows}</div><div class="label">总表行数</div></div>
        <div class="stat-card"><div class="number">${data.columns.length}</div><div class="label">字段数</div></div>
        <div class="stat-card"><div class="number">${data.order_count || 0}</div><div class="label">采购SKU数</div></div>
    `;

    const thead = document.querySelector("#dataTable thead");
    const tbody = document.querySelector("#dataTable tbody");
    thead.innerHTML = "";
    tbody.innerHTML = "";

    if (data.columns.length > 0) {
        const tr = document.createElement("tr");
        data.columns.forEach((col) => {
            const th = document.createElement("th");
            th.textContent = col;
            tr.appendChild(th);
        });
        thead.appendChild(tr);
    }

    data.preview.forEach((row) => {
        const tr = document.createElement("tr");
        data.columns.forEach((col) => {
            const td = document.createElement("td");
            const val = row[col];
            td.textContent = val !== null && val !== undefined ? val : "";
            tr.appendChild(td);
        });
        tbody.appendChild(tr);
    });

    result.classList.remove("hidden");
}

function showProgress() {
    progress.classList.remove("hidden");
}

function hideProgress() {
    progress.classList.add("hidden");
}

function showError(msg) {
    error.textContent = msg;
    error.classList.remove("hidden");
}

function hideError() {
    error.classList.add("hidden");
}

function hideResult() {
    result.classList.add("hidden");
}
