/** GoalCert brand mark — a circular "G" with a checkmark, drawn as SVG so it scales crisply. */
export function Logo({ size = 34, color = "currentColor" }: { size?: number; color?: string }) {
  const w = Math.round(size * 0.31);
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" fill="none" role="img" aria-label="GoalCert">
      {/* G — near-full ring with an inner bar on the right */}
      <path d="M78 33 A37 37 0 1 0 80 62 L54 62"
        stroke={color} strokeWidth={w} strokeLinecap="round" strokeLinejoin="round" fill="none" />
      {/* checkmark inside */}
      <path d="M31 51 L46 65 L70 35"
        stroke={color} strokeWidth={w} strokeLinecap="round" strokeLinejoin="round" fill="none" />
    </svg>
  );
}

/** Mark + wordmark, used in the sidebar / login form. */
export function Wordmark({ size = 30, color = "#15101f" }: { size?: number; color?: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 9 }}>
      <Logo size={Math.round(size * 1.15)} color={color} />
      <span style={{ fontSize: size * 0.62, fontWeight: 700, letterSpacing: "-.3px", color }}>Goalcert</span>
    </div>
  );
}
