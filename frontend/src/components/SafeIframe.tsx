import React, { useEffect, useRef } from "react";

// Runtime guard: a multi-MB inline blob injected via doc.write() crashes the React
// tree (the 5 MB Plotly trap). Charts must render from JSON (recharts), not inline
// HTML. Anything over this cap is refused with a visible notice instead of crashing.
const MAX_SRCDOC_BYTES = 1_000_000; // 1 MB

interface SafeIframeProps extends React.IframeHTMLAttributes<HTMLIFrameElement> {
  srcDocContent?: string | null;
}

export default function SafeIframe({ srcDocContent, ...props }: SafeIframeProps) {
  const iframeRef = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    if (iframeRef.current && srcDocContent) {
      const byteLength =
        typeof Blob !== "undefined"
          ? new Blob([srcDocContent]).size
          : srcDocContent.length;

      const doc = iframeRef.current.contentWindow?.document;
      if (!doc) return;

      if (byteLength > MAX_SRCDOC_BYTES) {
        // Refuse the oversized blob — render JSON-driven charts (recharts) instead.
        console.error(
          `SafeIframe: refused srcDoc of ${byteLength} bytes (> ${MAX_SRCDOC_BYTES}). ` +
            "Inline HTML this large crashes React; render charts from JSON (chart_data) via recharts.",
        );
        doc.open();
        doc.write(
          `<!doctype html><meta charset="utf-8"><body style="font:14px system-ui;padding:1rem;color:#b00">` +
            `Content too large to display inline (${(byteLength / 1_048_576).toFixed(1)} MB). ` +
            `Charts render from data, not inline HTML.</body>`,
        );
        doc.close();
        return;
      }

      doc.open();
      doc.write(srcDocContent);
      doc.close();
    } else if (iframeRef.current && !srcDocContent && props.src) {
      iframeRef.current.src = props.src;
    }
  }, [srcDocContent, props.src]);

  return <iframe ref={iframeRef} {...props} />;
}
