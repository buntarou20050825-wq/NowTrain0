// frontend/src/components/SearchScreen.jsx
import { useState, useRef, useCallback, useEffect } from "react";
import { searchStations, searchRoute } from "../api/serverData";
import "./SearchScreen.css";

/**
 * Phase 1: 検索画面 (Apple-style design)
 */
export default function SearchScreen({ onSearchComplete, initialParams }) {
  // 入力状態（initialParamsがある場合は復元）
  const [fromInput, setFromInput] = useState(initialParams?.fromStation || "");
  const [toInput, setToInput] = useState(initialParams?.toStation || "");
  const [selectedFrom, setSelectedFrom] = useState(null);
  const [selectedTo, setSelectedTo] = useState(null);
  // ユーザーが日時を変更したかどうかのフラグ
  // false(デフォルト): 常に現在時刻を表示 / true: ユーザー指定時刻を保持
  const [isTimeModified, setIsTimeModified] = useState(initialParams?.isTimeModified || false);

  const [date, setDate] = useState(() => {
    // 変更済みの場合は保持された値を復元
    if (initialParams?.isTimeModified && initialParams?.date) {
      return initialParams.date;
    }
    // 未変更なら現在日付 (ローカル時間)
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, "0");
    const day = String(now.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  });

  const [time, setTime] = useState(() => {
    // 変更済みの場合は保持された値を復元
    if (initialParams?.isTimeModified && initialParams?.time) {
      return initialParams.time;
    }
    // 未変更なら現在時刻
    const now = new Date();
    return now.toTimeString().slice(0, 5);
  });
  const [arriveBy, setArriveBy] = useState(false);

  // オートコンプリート状態
  const [fromSuggestions, setFromSuggestions] = useState([]);
  const [toSuggestions, setToSuggestions] = useState([]);
  const [showFromSuggestions, setShowFromSuggestions] = useState(false);
  const [showToSuggestions, setShowToSuggestions] = useState(false);

  // 検索状態
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // デバウンス用ref
  const fromDebounceRef = useRef(null);
  const toDebounceRef = useRef(null);
  const dateInputRef = useRef(null);
  const timeInputRef = useRef(null);

  // Case A: ユーザーが未変更の場合、現在時刻を維持し続ける (1分毎 or フォーカス時)
  // useEffect を使ってコンポーネント表示中も時刻を更新
  useEffect(() => {
    if (isTimeModified) return;

    const updateToNow = () => {
      const now = new Date();
      const year = now.getFullYear();
      const month = String(now.getMonth() + 1).padStart(2, "0");
      const day = String(now.getDate()).padStart(2, "0");
      setDate(`${year}-${month}-${day}`);
      setTime(now.toTimeString().slice(0, 5));
    };

    // マウント時に一度更新 (initでもやってるが念のため)
    updateToNow();

    const interval = setInterval(updateToNow, 60000); // 1分ごとに更新
    const onFocus = () => updateToNow(); // ウィンドウフォーカス時にも更新

    window.addEventListener("focus", onFocus);
    return () => {
      clearInterval(interval);
      window.removeEventListener("focus", onFocus);
    };
  }, [isTimeModified]);

  // 駅名検索（デバウンス付き）
  const searchStationsDebounced = useCallback((query, setSuggestions, setShow) => {
    if (query.length < 1) {
      setSuggestions([]);
      setShow(false);
      return;
    }
    searchStations(query, 8).then((data) => {
      setSuggestions(data.stations || []);
      setShow(true);
    });
  }, []);

  // 出発駅入力変更
  const handleFromInputChange = (e) => {
    const value = e.target.value;
    setFromInput(value);
    setSelectedFrom(null);

    if (fromDebounceRef.current) clearTimeout(fromDebounceRef.current);
    fromDebounceRef.current = setTimeout(() => {
      searchStationsDebounced(value, setFromSuggestions, setShowFromSuggestions);
    }, 300);
  };

  // 到着駅入力変更
  const handleToInputChange = (e) => {
    const value = e.target.value;
    setToInput(value);
    setSelectedTo(null);

    if (toDebounceRef.current) clearTimeout(toDebounceRef.current);
    toDebounceRef.current = setTimeout(() => {
      searchStationsDebounced(value, setToSuggestions, setShowToSuggestions);
    }, 300);
  };

  // 駅選択
  const handleSelectFrom = (station) => {
    setFromInput(station.name_ja);
    setSelectedFrom(station);
    setShowFromSuggestions(false);
  };

  const handleSelectTo = (station) => {
    setToInput(station.name_ja);
    setSelectedTo(station);
    setShowToSuggestions(false);
  };

  // 駅入れ替え
  const handleSwapStations = () => {
    const tempInput = fromInput;
    const tempSelected = selectedFrom;
    setFromInput(toInput);
    setSelectedFrom(selectedTo);
    setToInput(tempInput);
    setSelectedTo(tempSelected);
  };

  // 日時変更ハンドラ (変更フラグを立てる)
  const handleDateChange = (e) => {
    setDate(e.target.value);
    setIsTimeModified(true);
  };

  const handleTimeChange = (e) => {
    setTime(e.target.value);
    setIsTimeModified(true);
  };

  // 経路検索実行
  const handleSearch = async () => {
    const fromStation = selectedFrom?.name_ja || fromInput;
    const toStation = selectedTo?.name_ja || toInput;

    if (!fromStation || !toStation) {
      setError("出発駅と到着駅を入力してください");
      return;
    }

    setLoading(true);
    setError("");

    const searchParams = {
      fromStation,
      toStation,
      date,
      time,
      arriveBy,
      isTimeModified, // 状態を保存するために含める
    };

    const result = await searchRoute(searchParams);

    setLoading(false);

    if (result.status === "error") {
      const errorMsg =
        typeof result.error === "object"
          ? result.error?.message || JSON.stringify(result.error)
          : result.error || "経路検索に失敗しました";
      setError(errorMsg);
    } else if (result.itineraries?.length === 0) {
      setError("経路が見つかりませんでした");
    } else {
      onSearchComplete(result, searchParams);
    }
  };

  // Enter キーで検索
  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !loading) {
      handleSearch();
    }
  };

  // 日付フォーマット（表示用）
  const formatDateDisplay = (dateStr) => {
    const d = new Date(dateStr);
    return `${d.getMonth() + 1}/${d.getDate()}`;
  };

  return (
    <div className="search-screen">
      {/* ヘッダー */}
      <div className="search-header">
        <h1 className="search-logo">NowTrain</h1>
        <p className="search-subtitle">どこへ行きますか？</p>
      </div>

      {/* 検索カード */}
      <div className="search-card">
        {/* 出発駅 */}
        <div className="input-group">
          <div className="input-label">
            <span className="input-dot departure"></span>
            <span>出発</span>
          </div>
          <div className="input-wrapper">
            <input
              type="text"
              value={fromInput}
              onChange={handleFromInputChange}
              onFocus={() => fromSuggestions.length > 0 && setShowFromSuggestions(true)}
              onBlur={() => setTimeout(() => setShowFromSuggestions(false), 200)}
              onKeyDown={handleKeyDown}
              placeholder="駅名を入力"
              className="station-input"
            />
            {showFromSuggestions && fromSuggestions.length > 0 && (
              <ul className="suggestions-list">
                {fromSuggestions.map((station) => (
                  <li key={station.id} onMouseDown={() => handleSelectFrom(station)}>
                    <div className="suggestion-content">
                      <span className="suggestion-name">{station.name_ja}</span>
                      <span className="suggestion-lines">
                        {station.lines?.slice(0, 3).join("・")}
                        {station.lines?.length > 3 && "..."}
                      </span>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        {/* 入れ替えボタン */}
        <button className="swap-button" onClick={handleSwapStations} type="button" title="出発駅と到着駅を入れ替え">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M17 4L17 20" />
            <path d="M17 20L13 16" />
            <path d="M17 20L21 16" />
            <path d="M7 20L7 4" />
            <path d="M7 4L3 8" />
            <path d="M7 4L11 8" />
          </svg>
        </button>

        {/* 到着駅 */}
        <div className="input-group">
          <div className="input-label">
            <span className="input-dot arrival"></span>
            <span>到着</span>
          </div>
          <div className="input-wrapper">
            <input
              type="text"
              value={toInput}
              onChange={handleToInputChange}
              onFocus={() => toSuggestions.length > 0 && setShowToSuggestions(true)}
              onBlur={() => setTimeout(() => setShowToSuggestions(false), 200)}
              onKeyDown={handleKeyDown}
              placeholder="駅名を入力"
              className="station-input"
            />
            {showToSuggestions && toSuggestions.length > 0 && (
              <ul className="suggestions-list">
                {toSuggestions.map((station) => (
                  <li key={station.id} onMouseDown={() => handleSelectTo(station)}>
                    <div className="suggestion-content">
                      <span className="suggestion-name">{station.name_ja}</span>
                      <span className="suggestion-lines">
                        {station.lines?.slice(0, 3).join("・")}
                        {station.lines?.length > 3 && "..."}
                      </span>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        {/* 日時選択 */}
        <div className="datetime-row">
          <div
            className="datetime-button"
            onClick={() => dateInputRef.current?.showPicker?.() || dateInputRef.current?.focus()}
          >
            <span className="datetime-value">{formatDateDisplay(date)}</span>
            <input
              ref={dateInputRef}
              type="date"
              value={date}
              onChange={handleDateChange}
              className="datetime-input-hidden"
            />
          </div>
          <div
            className="datetime-button"
            onClick={() => timeInputRef.current?.showPicker?.() || timeInputRef.current?.focus()}
          >
            <span className="datetime-value">{time}</span>
            <input
              ref={timeInputRef}
              type="time"
              value={time}
              onChange={handleTimeChange}
              className="datetime-input-hidden"
            />
          </div>
        </div>

        {/* 到着/出発切り替え */}
        <div className="arrive-by-toggle">
          <button
            className={`toggle-option ${!arriveBy ? "active" : ""}`}
            onClick={() => setArriveBy(false)}
          >
            出発
          </button>
          <button
            className={`toggle-option ${arriveBy ? "active" : ""}`}
            onClick={() => setArriveBy(true)}
          >
            到着
          </button>
        </div>

        {/* 検索ボタン */}
        <button
          className="search-button"
          onClick={handleSearch}
          disabled={loading}
        >
          {loading ? "検索中..." : "経路を検索"}
        </button>

        {/* エラー表示 */}
        {error && <div className="search-error">{error}</div>}
      </div>
    </div>
  );
}
