// frontend/src/components/ResultsScreen.jsx
import React, { useState } from "react";

/**
 * Phase 2: 結果一覧画面 (Apple-style design with inline styles)
 */
export default function ResultsScreen({ results, searchParams, onSelect, onBack }) {
  const itineraries = results?.itineraries || [];
  const [selectedIndex, setSelectedIndex] = useState(null);

  // 時刻フォーマット
  const formatTime = (isoString) => {
    if (!isoString) return "";
    const date = new Date(isoString);
    return date.toLocaleTimeString("ja-JP", { hour: "2-digit", minute: "2-digit" });
  };

  // 日付フォーマット
  const formatDateDisplay = () => {
    if (!searchParams?.date) return "今日";
    const d = new Date(searchParams.date);
    const today = new Date();
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);

    if (d.toDateString() === today.toDateString()) return "今日";
    if (d.toDateString() === tomorrow.toDateString()) return "明日";
    return `${d.getMonth() + 1}/${d.getDate()}`;
  };

  // 乗換回数カウント
  const countTransfers = (legs) => {
    const transitLegs = legs.filter((leg) => leg.mode !== "WALK");
    return Math.max(0, transitLegs.length - 1);
  };

  // 運賃計算（仮）
  const calculateFare = (itinerary) => {
    if (itinerary.fare?.total) {
      return itinerary.fare.total;
    }
    return "---";
  };

  // 路線情報取得
  const getRouteInfo = (leg) => {
    const routeName = leg.route?.short_name || leg.route?.long_name || "";
    const routeColor = leg.route?.color ? `#${leg.route.color}` : "#007AFF";
    return { routeName, routeColor };
  };

  return (
    <div style={styles.container}>
      {/* ヘッダー */}
      <header style={styles.header}>
        <button style={styles.backButton} onClick={onBack}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
            <path d="M15 18l-6-6 6-6" />
          </svg>
          <span>戻る</span>
        </button>
        <div style={styles.headerTitle}>
          <span style={styles.headerRoute}>{searchParams?.fromStation} → {searchParams?.toStation}</span>
          <span style={styles.headerDate}>{formatDateDisplay()} {searchParams?.time || ""}出発</span>
        </div>
        <div style={styles.headerSpacer}></div>
      </header>

      {/* 結果サマリー */}
      <div style={styles.summary}>
        <span style={styles.summaryText}>{itineraries.length}件の経路が見つかりました</span>
      </div>

      {/* 経路リスト */}
      <main style={styles.main}>
        {itineraries.map((itinerary, index) => {
          const isSelected = selectedIndex === index;
          const isRecommended = index === 0;
          const transferCount = countTransfers(itinerary.legs);
          const transitLegs = itinerary.legs.filter((leg) => leg.mode !== "WALK");
          // 最初と最後の電車leg（タイムラインと時刻を一致させるため）
          const firstTransitLeg = transitLegs[0];
          const lastTransitLeg = transitLegs[transitLegs.length - 1];

          return (
            <div
              key={index}
              style={{
                ...styles.routeCard,
                ...(isSelected ? styles.routeCardSelected : {})
              }}
              onClick={() => setSelectedIndex(isSelected ? null : index)}
            >
              {/* おすすめバッジ */}
              {isRecommended && (
                <div style={styles.recommendedBadge}>
                  <span style={styles.recommendedIcon}>⚡</span>
                  おすすめ
                </div>
              )}

              {/* メイン情報 */}
              <div style={styles.routeMain}>
                {/* 時刻表示 */}
                <div style={styles.timeSection}>
                  <div style={styles.timeBlock}>
                    {/* 電車legの時刻を使用（徒歩は除外） */}
                    <span style={styles.timeValue}>{formatTime(firstTransitLeg?.start_time || itinerary.start_time)}</span>
                    <span style={styles.stationName}>{searchParams?.fromStation}</span>
                  </div>
                  <div style={styles.arrowSection}>
                    <div style={styles.arrowLine}></div>
                    <span style={styles.duration}>{itinerary.duration_minutes}分</span>
                    <div style={styles.arrowLine}></div>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#86868B" strokeWidth="2">
                      <path d="M9 18l6-6-6-6" />
                    </svg>
                  </div>
                  <div style={styles.timeBlock}>
                    <span style={styles.timeValue}>{formatTime(lastTransitLeg?.end_time || itinerary.end_time)}</span>
                    <span style={styles.stationName}>{searchParams?.toStation}</span>
                  </div>
                </div>

                {/* サブ情報 */}
                <div style={styles.metaSection}>
                  <div style={styles.metaItem}>
                    <span style={styles.metaIcon}>🔄</span>
                    <span style={styles.metaText}>
                      {transferCount === 0 ? "乗換なし" : `乗換 ${transferCount}回`}
                    </span>
                  </div>
                  <div style={styles.metaItem}>
                    <span style={styles.metaIcon}>💴</span>
                    <span style={styles.metaText}>{calculateFare(itinerary)}円</span>
                  </div>
                </div>
              </div>

              {/* 路線バッジ */}
              <div style={styles.linesSection}>
                {transitLegs.map((leg, legIndex) => {
                  const { routeName, routeColor } = getRouteInfo(leg);
                  return (
                    <React.Fragment key={legIndex}>
                      <div
                        style={{
                          ...styles.lineBadge,
                          background: routeColor,
                        }}
                      >
                        <span style={styles.lineName}>{routeName || leg.route?.long_name?.slice(0, 8) || "電車"}</span>
                      </div>
                      {legIndex < transitLegs.length - 1 && (
                        <span style={styles.lineConnector}>→</span>
                      )}
                    </React.Fragment>
                  );
                })}
              </div>

              {/* 展開時の詳細 */}
              {isSelected && (
                <div style={styles.expandedSection}>
                  <div style={styles.expandedDivider}></div>
                  <div style={styles.legsList}>
                    {itinerary.legs.map((leg, legIndex) => {
                      const { routeName, routeColor } = getRouteInfo(leg);
                      const isWalk = leg.mode === "WALK";
                      const isLastLeg = legIndex === itinerary.legs.length - 1;

                      // 最初/最後のWALKは非表示、途中のWALKは乗換として表示
                      const isFirstLeg = legIndex === 0;
                      const isLastLegInArray = legIndex === itinerary.legs.length - 1;
                      if (isWalk && (isFirstLeg || isLastLegInArray || leg.duration_minutes < 2)) return null;

                      return (
                        <div key={legIndex} style={styles.legItem}>
                          <div style={styles.legTimeline}>
                            <div style={{ ...styles.legDot, background: isWalk ? "#86868B" : routeColor }}></div>
                            {!isLastLeg && (
                              <div style={{ ...styles.legLine, background: isWalk ? "#E5E5EA" : routeColor }}></div>
                            )}
                          </div>
                          <div style={styles.legContent}>
                            <div style={styles.legHeader}>
                              <span style={styles.legTime}>{formatTime(leg.start_time)}</span>
                              <span style={styles.legStation}>{leg.from?.name}</span>
                            </div>
                            <div style={styles.legInfo}>
                              {isWalk ? (
                                <span style={styles.legWalk}>🚶 徒歩 {leg.duration_minutes}分</span>
                              ) : (
                                <>
                                  <span style={{ ...styles.legLineBadge, background: routeColor }}>
                                    {routeName || leg.route?.long_name || ""}
                                  </span>
                                  {leg.headsign && (
                                    <span style={styles.legDirection}>{leg.headsign}方面</span>
                                  )}
                                </>
                              )}
                            </div>
                            <div style={styles.legHeader}>
                              <span style={styles.legTime}>{formatTime(leg.end_time)}</span>
                              <span style={styles.legStation}>{leg.to?.name}</span>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                  <button
                    style={styles.selectButton}
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelect(itinerary);
                    }}
                  >
                    この経路でナビ開始
                  </button>
                </div>
              )}
            </div>
          );
        })}
      </main>
    </div>
  );
}

const styles = {
  container: {
    minHeight: "100vh",
    background: "#F5F5F7",
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
  },
  header: {
    position: "sticky",
    top: 0,
    background: "rgba(255, 255, 255, 0.9)",
    backdropFilter: "blur(20px)",
    WebkitBackdropFilter: "blur(20px)",
    padding: "12px 16px",
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    borderBottom: "1px solid rgba(0, 0, 0, 0.1)",
    zIndex: 100,
  },
  backButton: {
    display: "flex",
    alignItems: "center",
    gap: "4px",
    padding: "8px 12px",
    background: "transparent",
    border: "none",
    borderRadius: "8px",
    cursor: "pointer",
    color: "#007AFF",
    fontSize: "15px",
    fontWeight: "600",
    transition: "background 0.2s",
  },
  headerTitle: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
  },
  headerRoute: {
    fontSize: "17px",
    fontWeight: "600",
    color: "#1D1D1F",
  },
  headerDate: {
    fontSize: "13px",
    color: "#86868B",
    marginTop: "2px",
  },
  headerSpacer: {
    width: "40px",
  },
  summary: {
    padding: "16px 20px 8px",
  },
  summaryText: {
    fontSize: "13px",
    color: "#86868B",
  },
  main: {
    padding: "8px 16px 32px",
    display: "flex",
    flexDirection: "column",
    gap: "12px",
    overflowY: "auto",
  },
  routeCard: {
    background: "#FFFFFF",
    borderRadius: "16px",
    padding: "16px",
    boxShadow: "0 2px 8px rgba(0, 0, 0, 0.04)",
    cursor: "pointer",
    transition: "all 0.2s",
    border: "2px solid transparent",
  },
  routeCardSelected: {
    border: "2px solid #007AFF",
    boxShadow: "0 4px 20px rgba(0, 122, 255, 0.15)",
  },
  recommendedBadge: {
    display: "inline-flex",
    alignItems: "center",
    gap: "4px",
    padding: "4px 10px",
    background: "linear-gradient(135deg, #FFD60A 0%, #FF9500 100%)",
    borderRadius: "12px",
    fontSize: "12px",
    fontWeight: "600",
    color: "#1D1D1F",
    marginBottom: "12px",
  },
  recommendedIcon: {
    fontSize: "12px",
  },
  routeMain: {
    marginBottom: "12px",
  },
  timeSection: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: "12px",
  },
  timeBlock: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
  },
  timeValue: {
    fontSize: "24px",
    fontWeight: "600",
    color: "#1D1D1F",
    letterSpacing: "-0.5px",
  },
  stationName: {
    fontSize: "13px",
    color: "#86868B",
    marginTop: "2px",
  },
  arrowSection: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    flex: 1,
    justifyContent: "center",
    padding: "0 16px",
  },
  arrowLine: {
    flex: 1,
    height: "1px",
    background: "#E5E5EA",
    maxWidth: "40px",
  },
  duration: {
    fontSize: "14px",
    fontWeight: "500",
    color: "#1D1D1F",
    background: "#F5F5F7",
    padding: "4px 10px",
    borderRadius: "10px",
  },
  metaSection: {
    display: "flex",
    gap: "16px",
  },
  metaItem: {
    display: "flex",
    alignItems: "center",
    gap: "4px",
  },
  metaIcon: {
    fontSize: "14px",
  },
  metaText: {
    fontSize: "14px",
    color: "#86868B",
  },
  linesSection: {
    display: "flex",
    alignItems: "center",
    gap: "6px",
    flexWrap: "wrap",
  },
  lineBadge: {
    padding: "6px 12px",
    borderRadius: "8px",
    display: "flex",
    alignItems: "center",
  },
  lineName: {
    fontSize: "13px",
    fontWeight: "600",
    color: "#FFFFFF",
    textShadow: "0 1px 2px rgba(0, 0, 0, 0.2)",
  },
  lineConnector: {
    fontSize: "12px",
    color: "#86868B",
  },
  expandedSection: {
    marginTop: "16px",
  },
  expandedDivider: {
    height: "1px",
    background: "#E5E5EA",
    marginBottom: "16px",
  },
  legsList: {
    display: "flex",
    flexDirection: "column",
    gap: "0",
  },
  legItem: {
    display: "flex",
    gap: "12px",
  },
  legTimeline: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    width: "16px",
  },
  legDot: {
    width: "12px",
    height: "12px",
    borderRadius: "50%",
    border: "2px solid #FFFFFF",
    boxShadow: "0 1px 3px rgba(0, 0, 0, 0.2)",
    flexShrink: 0,
  },
  legLine: {
    width: "3px",
    flex: 1,
    minHeight: "60px",
    borderRadius: "2px",
    opacity: 0.5,
  },
  legContent: {
    flex: 1,
    paddingBottom: "20px",
  },
  legHeader: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    marginBottom: "4px",
  },
  legTime: {
    fontSize: "15px",
    fontWeight: "600",
    color: "#1D1D1F",
    width: "45px",
  },
  legStation: {
    fontSize: "15px",
    color: "#1D1D1F",
  },
  legInfo: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    margin: "8px 0 8px 53px",
  },
  legLineBadge: {
    fontSize: "12px",
    fontWeight: "600",
    color: "#FFFFFF",
    padding: "4px 8px",
    borderRadius: "6px",
  },
  legDirection: {
    fontSize: "13px",
    color: "#86868B",
  },
  legWalk: {
    fontSize: "13px",
    color: "#86868B",
    fontStyle: "italic",
  },
  selectButton: {
    width: "100%",
    padding: "14px",
    fontSize: "16px",
    fontWeight: "600",
    color: "#FFFFFF",
    background: "#007AFF",
    border: "none",
    borderRadius: "12px",
    cursor: "pointer",
    marginTop: "8px",
    transition: "all 0.2s",
  },
};
