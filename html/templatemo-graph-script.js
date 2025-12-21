document.addEventListener("DOMContentLoaded", () => {

    const btn = document.getElementById("crawlBtn");
    const loading = document.getElementById("loadingMessage");
const tableBody = document.querySelector("#resultTable tbody");
const resultArea = document.querySelector(".result-area");
    btn.addEventListener("click", async () => {

        console.log("버튼 눌림");

        btn.disabled = true;
        btn.style.backgroundColor = "#ff4d4d";
        btn.textContent = "검색 중...";

loading.style.display = "block";
tableBody.innerHTML = "";
resultArea.style.display = "none";
        const tp = document.querySelector("input[name='tp']:checked").value;
        const addrType = document.querySelector("input[name='addrType']:checked").value;

        const data = {
            tp: tp,
            addr: addrType,
            sido: document.getElementById("sido").value,
            sigungu: document.getElementById("sigungu").value,
            road: document.getElementById("road").value,
            bldg: document.getElementById("bldg").value
        };

       try {
    const res = await fetch("http://127.0.0.1:8000/api/crawl", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(data)
    });

if (!res.ok) {
    if (res.status === 400) {
        throw new Error("검색 결과 없음");
    }
    if (res.status === 500) {
        throw new Error("검색 결과 없음");
    }
    throw new Error("알 수 없는 오류");
}
    const result = await res.json();

    if (!result.result || result.result.length === 0) {
        const tr = document.createElement("tr");
        tr.innerHTML = `<td colspan="5" style="text-align:center;">검색 결과가 없습니다</td>`;
        tableBody.appendChild(tr); 
resultArea.style.display = "block";

    } else {
        result.result.forEach(item => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td>${item["전용면적(m^2)"]}</td>
                <td>${item["계약기간"]}</td>
                <td>${item["보증금(만원)"]}</td>
                <td>${item["월세(만원)"]}</td>
                <td>${item["계약구분"]}</td>
            `;
            tableBody.appendChild(tr);
resultArea.style.display = "block";
        });

    }

} catch (e) {
    alert("오류 발생: " + e.message);
} finally {loading.style.display = "none";
            btn.disabled = false;
            btn.style.backgroundColor = "#4CAF50";
            btn.textContent = "검색";
        }

    });
});
