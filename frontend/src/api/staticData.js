/**
 * 静的データ取得API
 * 
 * 設計変更: 直接JSONファイルを読む代わりに、バックエンドAPIを経由する。
 * これにより、ID解決 (chuo_rapid -> JR-East.ChuoRapid) がバックエンドで行われる。
 */

const API_BASE = "";  // 同一オリジン (Vite proxies /api to backend)
const LOCAL_DATA_PATH = "/data/mini-tokyo-3d";

async function fetchJson(path) {
  try {
    const res = await fetch(path);
    if (!res.ok) throw new Error(`Failed to fetch ${path}: ${res.status}`);
    return await res.json();
  } catch (error) {
    console.error(`Error fetching ${path}:`, error);
    return null;
  }
}

/**
 * 全路線データを取得 (ローカルJSONから)
 * App.jsx の updateStaticMap で使用
 */
export function fetchRailways() {
  return fetchJson(`${LOCAL_DATA_PATH}/railways.json`);
}

/**
 * 全駅データを取得 (ローカルJSONから)
 * App.jsx の updateStaticMap で使用
 */
export function fetchStations() {
  return fetchJson(`${LOCAL_DATA_PATH}/stations.json`);
}

/**
 * 座標データを取得 (ローカルJSONから)
 * App.jsx の updateStaticMap で使用
 */
export function fetchCoordinates() {
  return fetchJson(`${LOCAL_DATA_PATH}/coordinates.json`);
}

// ============================================================================
// 新規追加: バックエンドAPI経由のデータ取得 (ID解決対応)
// ============================================================================

/**
 * 駅データを取得 (バックエンドAPI経由)
 * ID解決: chuo_rapid -> JR-East.ChuoRapid
 * 
 * @param {string} lineId - 路線ID (例: "chuo_rapid")
 * @returns {Promise<{stations: Array}>}
 */
export async function fetchStationsByLine(lineId) {
  if (!lineId) {
    console.error('[fetchStationsByLine] lineId is required');
    return { stations: [] };
  }

  const data = await fetchJson(`${API_BASE}/api/stations?lineId=${encodeURIComponent(lineId)}`);
  return data || { stations: [] };
}

/**
 * 線路形状データを取得 (バックエンドAPI経由)
 * ID解決: chuo_rapid -> JR-East.ChuoRapid
 * 
 * @param {string} lineId - 路線ID (例: "chuo_rapid")
 * @returns {Promise<{type: "FeatureCollection", features: Array}>}
 */
export async function fetchShapesByLine(lineId) {
  if (!lineId) {
    console.error('[fetchShapesByLine] lineId is required');
    return { type: "FeatureCollection", features: [] };
  }

  const data = await fetchJson(`${API_BASE}/api/shapes?lineId=${encodeURIComponent(lineId)}`);
  return data || { type: "FeatureCollection", features: [] };
}

/**
 * 路線詳細を取得 (バックエンドAPI経由)
 * ID解決: chuo_rapid -> JR-East.ChuoRapid
 * 
 * @param {string} lineId - 路線ID (例: "chuo_rapid")
 */
export async function fetchLineDetail(lineId) {
  if (!lineId) {
    console.error('[fetchLineDetail] lineId is required');
    return null;
  }

  return await fetchJson(`${API_BASE}/api/lines/${encodeURIComponent(lineId)}`);
}
