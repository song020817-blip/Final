document.addEventListener("DOMContentLoaded", () => {
  const btn = document.getElementById("predictBtn");
  const resultBox = document.getElementById("resultBox");

  btn.addEventListener("click", async () => {
    const payload = {
      address: document.getElementById("address").value.trim(),
      area: parseFloat(document.getElementById("area").value),
      floor: parseInt(document.getElementById("floor").value),
      year_built: parseInt(document.getElementById("year_built").value),
      housing_type: document.getElementById("housing_type").value,
      rent_type: document.getElementById("rent_type").value,
    };

    if (!payload.address) {
      resultBox.innerText = "❗ 주소를 입력해주세요.";
      return;
    }

    resultBox.innerText = "⏳ 예측 중...";

    try {
      const res = await fetch("/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) throw new Error("API error");

      const data = await res.json();

      resultBox.innerHTML = `
        💰 보증금 예측: <b>${data.deposit_pred.toLocaleString()} 만원</b><br>
        🧾 월세 예측: <b>${data.monthly_pred.toLocaleString()} 만원</b>
      `;
    } catch (e) {
      resultBox.innerText = "❌ 예측 실패 (서버/네트워크 오류)";
    }
  });
});
