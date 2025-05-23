// components/DockerVNCViewer.tsx
"use client"; // Designates this as a Client Component

import React, { useEffect, useState } from 'react';

interface DockerVNCViewerProps {
  /**
   * The base URL of the noVNC server (e.g., http://localhost:8005).
   * This is the host port you mapped to container port 6080.
   */
  noVncBaseUrl: string;
  /**
   * The VNC password for the session.
   */
  vncPassword?: string;
  /**
   * Width of the VNC viewer iframe. Defaults to '100%'.
   */
  width?: string | number;
  /**
   * Height of the VNC viewer iframe. Defaults to '768px'.
   */
  height?: string | number;
  /**
   * Title for the iframe, for accessibility. Defaults to 'Sandbox Browser'.
   */
  title?: string;
  /**
   * Optional flag to show connection controls within the noVNC UI.
   * Defaults to false (usually preferred for embedding).
   */
  showControls?: boolean;
}

const DockerVNCViewer: React.FC<DockerVNCViewerProps> = ({
  noVncBaseUrl,
  vncPassword,
  width = '100%',
  height = '100%',
  title = 'Sandbox Browser',
  showControls = false,
}) => {
  const [iframeSrc, setIframeSrc] = useState<string>('');

  useEffect(() => {
    // Construct the noVNC URL.
    // The `vnc.html` is the typical entry point for the noVNC client.
    // Parameters like `autoconnect`, `password`, `host`, `port` can be passed in the query string.
    // `launch.sh` (or `novnc_proxy`) inside the container handles proxying to the actual VNC server (x11vnc).
    // When `launch.sh` is used with `--vnc localhost:5901`, it sets up websockify to listen on its
    // own port (6080 in container) and proxy to that VNC target.
    // The client connecting to noVNC (the iframe) just needs to know the websockify URL.

    const params = new URLSearchParams();
    if (vncPassword) {
      params.append('password', vncPassword);
    }
    // `autoconnect=true` can be useful if you don't want the user to click "Connect"
    params.append('autoconnect', 'true'); 

    // If showControls is false, we might want to hide the noVNC control bar.
    // This is usually done via `?hide_status_bar=true` or similar, but check noVNC docs for exact params.
    // For simplicity, we'll just control basic connection params here.
    // A more advanced setup might involve a custom noVNC UI.
    // params.append('show_dot', 'false'); // Example to hide the dot cursor
    // params.append('stylesheet', 'your-custom-styles.css'); // Example for custom styling

    // The host and port for noVNC client JavaScript should be the ones it's served from.
    // If noVncBaseUrl is "http://localhost:8005", then the JS in vnc.html will attempt to
    // connect to "ws://localhost:8005".
    // The launch.sh script handles the internal proxy from container's 6080 to 5901.
    
    let url = `${noVncBaseUrl.replace(/\/$/, '')}/vnc.html`; // Ensure no trailing slash on base URL
    if (params.toString()) {
      url += `?${params.toString()}`;
    }
    
    setIframeSrc(url);

  }, [noVncBaseUrl, vncPassword, showControls]);

  if (!iframeSrc) {
    return <div>Loading VNC viewer...</div>;
  }

  return (
    <iframe
      src={iframeSrc}
      width={width}
      height={height}
      style={{ border: '1px solid #ccc', height: '100%' }} // Ensure iframe fills container height
      title={title}
      // Iframe sandbox attributes:
      // "allow-scripts": Necessary for noVNC to function.
      // "allow-same-origin": noVNC client scripts need to interact with the WebSocket server on the same origin.
      // "allow-forms": If there are any forms within the noVNC UI itself (e.g., password prompt if not in URL).
      sandbox="allow-scripts allow-same-origin allow-forms"
    />
  );
};

export default DockerVNCViewer;