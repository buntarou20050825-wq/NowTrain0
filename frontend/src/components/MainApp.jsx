// frontend/src/components/MainApp.jsx
import { useState, useCallback } from "react";
import SearchScreen from "./SearchScreen";
import ResultsScreen from "./ResultsScreen";
import NavigationScreen from "./NavigationScreen";
import "./MainApp.css";

/**
 * 3フェーズ UI/UX メインコンポーネント
 *
 * Phase 1: search     - 検索画面（地図なし）
 * Phase 2: results    - 結果一覧（地図なし）
 * Phase 3: navigation - ナビゲーション（地図表示）
 */
export default function MainApp() {
  const [phase, setPhase] = useState("search");
  const [searchResults, setSearchResults] = useState(null);
  const [searchParams, setSearchParams] = useState(null);
  const [selectedItinerary, setSelectedItinerary] = useState(null);

  // Phase 1 → Phase 2: 検索完了時
  const handleSearchComplete = useCallback((results, params) => {
    setSearchResults(results);
    setSearchParams(params);
    setPhase("results");
  }, []);

  // Phase 2 → Phase 3: 経路選択時
  const handleSelectRoute = useCallback((itinerary) => {
    setSelectedItinerary(itinerary);
    setPhase("navigation");
  }, []);

  // 戻るボタン
  const handleBack = useCallback(() => {
    if (phase === "results") {
      setPhase("search");
    } else if (phase === "navigation") {
      setPhase("results");
    }
  }, [phase]);

  // 最初からやり直す（Phase 3 → Phase 1）
  const handleNewSearch = useCallback(() => {
    setSelectedItinerary(null);
    setSearchResults(null);
    setSearchParams(null);
    setPhase("search");
  }, []);

  return (
    <div className="main-app">
      {phase === "search" && (
        <SearchScreen
          onSearchComplete={handleSearchComplete}
          initialParams={searchParams}
        />
      )}
      {phase === "results" && (
        <ResultsScreen
          results={searchResults}
          searchParams={searchParams}
          onSelect={handleSelectRoute}
          onBack={handleBack}
        />
      )}
      {phase === "navigation" && (
        <NavigationScreen
          itinerary={selectedItinerary}
          searchParams={searchParams}
          onBack={handleBack}
          onNewSearch={handleNewSearch}
        />
      )}
    </div>
  );
}
