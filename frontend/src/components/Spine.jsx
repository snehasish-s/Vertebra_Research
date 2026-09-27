export default function Spine({ active = 2, compact = false }) {
  return (
    <svg
      className={`spine ${compact ? "compact" : ""}`}
      viewBox="0 0 360 700"
      role="img"
      aria-label="Illustrated human spine connecting the seven stages of document research"
    >
      <defs>
        <linearGradient
          id={compact ? "boneSmall" : "bone"}
          x1="0"
          x2="1"
          y1="0"
          y2="1"
        >
          <stop offset="0" stopColor="#fefdf6" />
          <stop offset=".55" stopColor="#dfddcc" />
          <stop offset="1" stopColor="#b2b7a2" />
        </linearGradient>
        <linearGradient id={compact ? "litSmall" : "lit"} x1="0" x2="1">
          <stop offset="0" stopColor="#c8eab6" />
          <stop offset=".5" stopColor="#e0f6c4" />
          <stop offset="1" stopColor="#91b977" />
        </linearGradient>
      </defs>
      <path
        d="M190 38 C135 140 215 215 184 322 S126 465 186 580 L183 643"
        fill="none"
        stroke="#b8bea9"
        strokeWidth="15"
      />
      {Array.from({ length: 24 }, (_, index) => {
        const y = 50 + index * 23;
        const x = 179 + Math.sin(index / 3.3) * 20;
        const scale = 0.64 + index * 0.025;
        const illuminated = Math.floor(index / 3.5) <= active;
        return (
          <g
            key={index}
            transform={`translate(${x} ${y}) rotate(${Math.cos(index / 3.3) * -8}) scale(${scale})`}
            className={`vertebra ${illuminated ? "illuminated" : ""}`}
          >
            <path
              d="M-30 -6 C-44 -16 -54 -16 -57 -8 L-41 5 -30 9 M30 -6 C44 -16 54 -16 57 -8 L41 5 30 9"
              fill={illuminated ? "#b9d7a3" : "#c7cbb9"}
              stroke="#9aa58b"
              strokeWidth="1"
            />
            <path
              d="M-29 -10 Q0 -20 29 -10 L34 5 Q28 19 0 17 Q-28 19 -34 5 Z"
              fill={`url(#${illuminated ? (compact ? "litSmall" : "lit") : compact ? "boneSmall" : "bone"})`}
              stroke={illuminated ? "#6e9659" : "#a3ad95"}
              strokeWidth="1.2"
            />
            <path
              d="M-23 -6 Q0 -11 23 -6 M-27 9 Q0 16 27 9"
              fill="none"
              stroke="#fffef8"
              strokeOpacity=".65"
              strokeWidth="2"
            />
            <path
              d="M-4 3 L0 26 6 5"
              fill={illuminated ? "#a4c48b" : "#bcc2ad"}
              opacity=".85"
            />
          </g>
        );
      })}
      <path
        d="M147 603 Q179 590 211 603 Q205 634 180 658 Q157 638 147 603Z"
        fill="#b4bfa2"
        stroke="#919f83"
      />
      <path
        d="M164 614 L193 614 M169 626 L188 626 M175 637 L184 637"
        stroke="#e4e6d4"
        strokeWidth="3"
      />
    </svg>
  );
}
