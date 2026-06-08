import React, { useEffect, useRef } from "react";

interface SafeIframeProps extends React.IframeHTMLAttributes<HTMLIFrameElement> {
  srcDocContent?: string | null;
}

export default function SafeIframe({ srcDocContent, ...props }: SafeIframeProps) {
  const iframeRef = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    if (iframeRef.current && srcDocContent) {
      const doc = iframeRef.current.contentWindow?.document;
      if (doc) {
        doc.open();
        doc.write(srcDocContent);
        doc.close();
      }
    } else if (iframeRef.current && !srcDocContent && props.src) {
        iframeRef.current.src = props.src;
    }
  }, [srcDocContent, props.src]);

  return <iframe ref={iframeRef} {...props} />;
}
