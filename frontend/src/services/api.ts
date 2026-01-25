const BASE_URL = "http://127.0.0.1:8000";

/* ---------------------------------------------
   REAL-TIME PREDICTION
---------------------------------------------- */
export async function getSilverPrediction() {
  const res = await fetch(`${BASE_URL}/silver/predict`);
  if (!res.ok) {
    throw new Error("Failed to fetch silver prediction");
  }
  return res.json();
}

/* ---------------------------------------------
   REAL HISTORICAL DATA (FOR GRAPH)
---------------------------------------------- */
export async function getSilverHistory() {
  const res = await fetch(`${BASE_URL}/silver/history`);
  if (!res.ok) {
    throw new Error("Failed to fetch silver history");
  }
  return res.json();
}
