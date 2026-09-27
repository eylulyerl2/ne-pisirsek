import { useState } from "react";

function Star({ filled, half = false }: { filled: boolean; half?: boolean }) {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true">
      {half && (
        <defs>
          <linearGradient id="star-half">
            <stop offset="50%" stopColor="currentColor" />
            <stop offset="50%" stopColor="transparent" />
          </linearGradient>
        </defs>
      )}
      <path
        d="M12 2.5l2.9 6.1 6.6.8-4.9 4.6 1.3 6.6L12 17.6l-5.9 3 1.3-6.6-4.9-4.6 6.6-.8Z"
        fill={half ? "url(#star-half)" : filled ? "currentColor" : "none"}
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/** Salt gösterim: ortalama puanı (küsuratlıysa yarım yıldızla) ve isteğe bağlı sayıyı gösterir. */
export function StarDisplay({ value, count }: { value: number | null; count?: number }) {
  if (value === null) return <span className="muted small">Henüz puanlanmamış</span>;
  const stars = [1, 2, 3, 4, 5].map((n) => (n <= Math.round(value * 2) / 2 ? (n - value <= 0.25 ? "full" : "half") : "empty"));
  return (
    <span className="star-display" aria-label={`${value.toFixed(1)} / 5 yıldız${count !== undefined ? `, ${count} puanlama` : ""}`}>
      <span className="stars" aria-hidden="true">
        {stars.map((kind, i) => (
          <Star key={i} filled={kind !== "empty"} half={kind === "half"} />
        ))}
      </span>
      <span className="muted small">
        {value.toFixed(1)}
        {count !== undefined ? ` (${count})` : ""}
      </span>
    </span>
  );
}

interface StarInputProps {
  value: number;
  onChange: (value: number) => void;
  disabled?: boolean;
}

/** Etkileşimli: tıklayarak 1-5 arası puan verir; klavyeyle de (ok tuşları) kullanılabilir. */
export function StarInput({ value, onChange, disabled }: StarInputProps) {
  const [hover, setHover] = useState<number | null>(null);
  const shown = hover ?? value;

  return (
    <div
      className="star-input"
      role="radiogroup"
      aria-label="Puanınız"
      onMouseLeave={() => setHover(null)}
      onKeyDown={(event) => {
        if (disabled) return;
        if (event.key === "ArrowRight" || event.key === "ArrowUp") {
          event.preventDefault();
          onChange(Math.min(5, value + 1));
        } else if (event.key === "ArrowLeft" || event.key === "ArrowDown") {
          event.preventDefault();
          onChange(Math.max(1, value - 1));
        }
      }}
    >
      {[1, 2, 3, 4, 5].map((n) => (
        <button
          key={n}
          type="button"
          className="star-btn"
          role="radio"
          aria-checked={value === n}
          aria-label={`${n} yıldız`}
          disabled={disabled}
          style={{ color: n <= shown ? "var(--course-soup)" : "var(--border)" }}
          onMouseEnter={() => setHover(n)}
          onFocus={() => setHover(n)}
          onBlur={() => setHover(null)}
          onClick={() => onChange(n)}
        >
          <Star filled={n <= shown} />
        </button>
      ))}
    </div>
  );
}
