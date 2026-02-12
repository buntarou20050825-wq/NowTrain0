// frontend/src/components/NavigationScreen.jsx
import { useMemo, useEffect, useState, useCallback } from "react";
import MapView from "./MapView";
import { extractTrainNumber, isSameTrain } from "../utils/trainUtils";
import { AVAILABLE_LINES, OTP_NUMERIC_ROUTE_MAP } from "../constants/lines";
import "./NavigationScreen.css";

// 英語路線名 → 内部ID マッピング
const ENGLISH_LINE_NAME_MAP = {
  "yamanote": "yamanote",
  "chuo rapid": "chuo_rapid",
  "chuo-sobu local": "sobu_local",
  "keihin-tohoku": "keihin_tohoku",
  "negishi": "keihin_tohoku",
  "tokaido": "tokaido",
  "yokosuka": "yokosuka",
  "sobu rapid": "sobu_rapid",
  "joban rapid": "joban_rapid",
  "joban local": "joban_local",
  "keiyo": "keiyo",
  "musashino": "musashino",
  "nambu": "nambu",
  "yokohama": "yokohama",
  "saikyo": "saikyo",
  "kawagoe": "kawagoe",
  "shonan-shinjuku": "shonan_shinjuku",
  "chuo": "chuo",
  "ome": "ome",
  "itsukaichi": "itsukaichi",
  "utsunomiya": "utsunomiya",
  "takasaki": "takasaki",
};

/**
 * OTP route から内部路線IDを取得
 */
const getInternalLineId = (route) => {
  if (!route) return null;

  const longName = (route.long_name || "").toLowerCase();
  if (longName) {
    for (const [keyword, lineId] of Object.entries(ENGLISH_LINE_NAME_MAP)) {
      if (longName.includes(keyword)) {
        return lineId;
      }
    }
    const line = AVAILABLE_LINES.find(
      (l) => longName.includes(l.name.toLowerCase()) || l.name.toLowerCase().includes(longName)
    );
    if (line) return line.id;
  }

  if (route.gtfs_id) {
    const parts = route.gtfs_id.split(":");
    if (parts.length > 1) {
      const routeIdPart = parts[1];
      if (routeIdPart.startsWith("JR-East.")) {
        const line = AVAILABLE_LINES.find((l) => l.railwayId === routeIdPart);
        if (line) return line.id;
      }
      // 数字ID形式 ("21" → "yokohama")
      const numericMatch = OTP_NUMERIC_ROUTE_MAP[routeIdPart];
      if (numericMatch) return numericMatch;
    }
  }

  const shortName = route.short_name || "";
  if (shortName) {
    const line = AVAILABLE_LINES.find(
      (l) => l.name.includes(shortName) || shortName.includes(l.name)
    );
    if (line) return line.id;
  }

  console.warn("[getInternalLineId] Could not match route:", route);
  return null;
};

/**
 * Phase 3: ナビゲーション画面 (Apple-style design with bottom sheet)
 */
export default function NavigationScreen({ itinerary, searchParams, onBack, onNewSearch }) {
  const [isSheetExpanded, setIsSheetExpanded] = useState(false);

  // 経路から My Train の trip_id リストを抽出
  const myTrainIds = useMemo(() => {
    if (!itinerary?.legs) return [];

    const ids = [];
    for (const leg of itinerary.legs) {
      if (leg.mode === "WALK") continue;

      const tripId = leg.trip_id;
      if (tripId) {
        const normalizedId = extractTrainNumber(tripId);
        if (normalizedId) {
          ids.push(normalizedId);
          console.log("[NavigationScreen] Extracted train:", normalizedId, "from", tripId);
        }
      }
    }
    return ids;
  }, [itinerary]);

  // 経路から使用する路線の内部IDリストを抽出
  const myLineIds = useMemo(() => {
    if (!itinerary?.legs) return [];

    const lineIds = new Set();
    for (const leg of itinerary.legs) {
      if (leg.mode === "WALK") continue;

      const internalLineId = getInternalLineId(leg.route);
      if (internalLineId) {
        lineIds.add(internalLineId);
        console.log("[NavigationScreen] Extracted lineId:", internalLineId, "from route:", leg.route);
      }
    }
    return Array.from(lineIds);
  }, [itinerary]);

  useEffect(() => {
    console.log("[NavigationScreen] myTrainIds:", myTrainIds);
    console.log("[NavigationScreen] myLineIds:", myLineIds);
  }, [myTrainIds, myLineIds]);

  // 運行状態を追跡
  const [runningTrains, setRunningTrains] = useState({});

  // 電車の運行状態をチェック
  const checkTrainStatus = useCallback(async () => {
    if (myLineIds.length === 0 || myTrainIds.length === 0) return;

    const status = {};

    for (const lineId of myLineIds) {
      try {
        const res = await fetch(`/api/trains/${lineId}/positions/v4`);
        if (res.ok) {
          const data = await res.json();
          const positions = data.positions || [];

          for (const trainId of myTrainIds) {
            const found = positions.find((p) =>
              isSameTrain(p.train_number, trainId)
            );
            if (found) {
              status[trainId] = {
                running: true,
                status: found.status,
                delay: found.delay || 0,
                isStarting: found.is_starting_station || false,
              };
            }
          }
        }
      } catch (err) {
        console.error(`[NavigationScreen] Failed to check train status for ${lineId}:`, err);
      }
    }

    for (const trainId of myTrainIds) {
      if (!status[trainId]) {
        status[trainId] = { running: false };
      }
    }

    setRunningTrains(status);
  }, [myLineIds, myTrainIds]);

  useEffect(() => {
    const t = setTimeout(checkTrainStatus, 0);
    const interval = setInterval(checkTrainStatus, 5000);
    return () => {
      clearTimeout(t);
      clearInterval(interval);
    };
  }, [checkTrainStatus]);

  // 時刻フォーマット
  const formatTime = (isoString) => {
    if (!isoString) return "";
    const date = new Date(isoString);
    return date.toLocaleTimeString("ja-JP", { hour: "2-digit", minute: "2-digit" });
  };

  // 所要時間フォーマット
  const formatDuration = (minutes) => {
    if (minutes < 60) return `${minutes}分`;
    const h = Math.floor(minutes / 60);
    const m = minutes % 60;
    return m > 0 ? `${h}時間${m}分` : `${h}時間`;
  };

  // 乗換回数カウント
  const countTransfers = () => {
    if (!itinerary?.legs) return 0;
    const transitLegs = itinerary.legs.filter((leg) => leg.mode !== "WALK");
    return Math.max(0, transitLegs.length - 1);
  };

  // 路線情報取得
  const getRouteInfo = (leg) => {
    const routeName = leg.route?.short_name || leg.route?.long_name || "";
    const routeColor = leg.route?.color ? `#${leg.route.color}` : "#007AFF";
    return { routeName, routeColor };
  };

  // 出発駅と到着駅
  // searchParamsの駅名を優先（OTPが"Origin"/"Destination"を返す場合の対策）
  const fromStation = searchParams?.fromStation || itinerary?.legs?.[0]?.from?.name?.replace(/駅$/, "") || "";
  const toStation = searchParams?.toStation || itinerary?.legs?.slice(-1)[0]?.to?.name?.replace(/駅$/, "") || "";

  // 最初と最後の電車leg（WALK以外）を探す
  // 上部サマリーの時刻はタイムラインと一致させるため、徒歩を除いた電車の時刻を使用
  const firstTransitLeg = itinerary?.legs?.find(leg => leg.mode !== "WALK");
  const lastTransitLeg = [...(itinerary?.legs || [])].reverse().find(leg => leg.mode !== "WALK");

  return (
    <div className="navigation-screen">
      {/* Floating Controls */}
      <div className="floating-controls">
        <button className="floating-button back" onClick={onBack}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M15 18L9 12L15 6" />
          </svg>
          結果に戻る
        </button>
        <button className="floating-button new-search" onClick={onNewSearch}>
          新しい検索
        </button>
      </div>

      {/* Map */}
      <div className="navigation-map">
        <MapView
          navigationMode={true}
          selectedItinerary={itinerary}
          myTrainIds={myTrainIds}
          myLineIds={myLineIds}
        />
      </div>

      {/* Bottom Sheet */}
      {itinerary && (
        <div className={`bottom-sheet ${isSheetExpanded ? "expanded" : ""}`}>
          {/* Drag Handle */}
          <div
            className="sheet-handle"
            onClick={() => setIsSheetExpanded(!isSheetExpanded)}
          >
            <div className="handle-bar"></div>
          </div>

          {/* Sheet Header (always visible) */}
          <div className="sheet-header" onClick={() => setIsSheetExpanded(!isSheetExpanded)}>
            <div className="sheet-route">
              <span className="sheet-from">{fromStation}</span>
              <span className="sheet-arrow">→</span>
              <span className="sheet-to">{toStation}</span>
            </div>
            <div className="sheet-times">
              {/* 電車legの時刻を使用してタイムラインと一致させる（徒歩は除外） */}
              <span className="sheet-time">{formatTime(firstTransitLeg?.start_time || itinerary.legs?.[0]?.start_time)}</span>
              <span className="sheet-time-arrow">―――→</span>
              <span className="sheet-time">{formatTime(lastTransitLeg?.end_time || itinerary.legs?.[itinerary.legs?.length - 1]?.end_time)}</span>
            </div>
            <div className="sheet-meta">
              <span>{formatDuration(itinerary.duration_minutes)}</span>
              <span className="meta-divider">|</span>
              <span>{countTransfers() === 0 ? "乗換なし" : `乗換${countTransfers()}回`}</span>
            </div>

            {/* Train Status Summary */}
            <div className="sheet-train-summary">
              {myTrainIds.map((trainId) => {
                const status = runningTrains[trainId];
                const isRunning = status?.running;
                const isStarting = status?.isStarting;
                return (
                  <div key={trainId} className={`train-chip ${isRunning ? "running" : ""} ${isStarting ? "starting" : ""}`}>
                    <span className="train-dot">{isRunning ? "●" : "○"}</span>
                    <span className="train-id">{trainId}</span>
                    <span className="train-label">{isStarting ? "当駅始発" : (isRunning ? "運行中" : "未検出")}</span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Sheet Content (expanded) */}
          {isSheetExpanded && (
            <div className="sheet-content">
              <div className="sheet-divider"></div>

              {/* Timeline */}
              <div className="sheet-timeline">
                {itinerary.legs.map((leg, legIdx) => {
                  const { routeName, routeColor } = getRouteInfo(leg);
                  const isWalk = leg.mode === "WALK";
                  const isLastLeg = legIdx === itinerary.legs.length - 1;

                  // Get train status for this leg
                  const tripId = leg.trip_id;
                  const normalizedId = tripId ? extractTrainNumber(tripId) : null;
                  const trainStatus = normalizedId ? runningTrains[normalizedId] : null;
                  const isRunning = trainStatus?.running;
                  const delay = trainStatus?.delay || 0;
                  const delayMin = Math.floor(delay / 60);

                  // 徒歩区間のフィルタリング:
                  // - 最初のleg(legIdx=0)がWALKなら非表示（出発地→最初の駅）
                  // - 最後のlegがWALKなら非表示（最後の駅→目的地）
                  // - 2分未満の徒歩は非表示
                  // - それ以外の途中のWALK（乗換）は表示
                  const isFirstLeg = legIdx === 0;
                  const isLastLegInArray = legIdx === itinerary.legs.length - 1;
                  if (isWalk && (isFirstLeg || isLastLegInArray || leg.duration_minutes < 2)) {
                    return null;
                  }

                  return (
                    <div key={legIdx} className="timeline-leg">
                      {/* From Station */}
                      <div className="timeline-station">
                        <div
                          className="timeline-dot"
                          style={{ borderColor: isWalk ? "#86868B" : routeColor }}
                        ></div>
                        <div className="timeline-station-info">
                          <span className="timeline-time">{formatTime(leg.start_time)}</span>
                          <span className="timeline-name">
                            {/* 最初のlegで"Origin"の場合は検索時の駅名を使用 */}
                            {legIdx === 0 && leg.from?.name === "Origin" ? fromStation : leg.from?.name}
                          </span>
                        </div>
                      </div>

                      {/* Line Info */}
                      <div
                        className="timeline-line"
                        style={{ borderColor: isWalk ? "#E5E5EA" : routeColor }}
                      >
                        {isWalk ? (
                          <span className="timeline-walk">徒歩 {leg.duration_minutes}分</span>
                        ) : (
                          <div className="timeline-transit">
                            <span className="timeline-route" style={{ color: routeColor }}>
                              {routeName || leg.route?.long_name || ""}
                              {leg.headsign ? ` (${leg.headsign})` : ""}
                            </span>
                            {normalizedId && (
                              <div className={`timeline-train-status ${isRunning ? "running" : ""} ${trainStatus?.isStarting ? "starting" : ""} ${delayMin >= 10 ? "severe-delay" : delayMin >= 5 ? "moderate-delay" : ""}`}>
                                <span className="status-dot">{isRunning ? "●" : "○"}</span>
                                <span className="status-id">{normalizedId}</span>
                                <span className="status-label">
                                  {trainStatus?.isStarting ? "当駅始発" : (isRunning ? "運行中" : "未検出")}
                                </span>
                                {isRunning && delayMin > 0 && (
                                  <span className="delay-badge">+{delayMin}分遅れ</span>
                                )}
                              </div>
                            )}
                          </div>
                        )}
                      </div>

                      {/* To Station (only for last leg) */}
                      {isLastLeg && (
                        <div className="timeline-station">
                          <div
                            className="timeline-dot filled"
                            style={{ backgroundColor: routeColor, borderColor: routeColor }}
                          ></div>
                          <div className="timeline-station-info">
                            <span className="timeline-time">{formatTime(leg.end_time)}</span>
                            <span className="timeline-name">
                              {/* 最後のlegで"Destination"の場合は検索時の駅名を使用 */}
                              {leg.to?.name === "Destination" ? toStation : leg.to?.name}
                            </span>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
