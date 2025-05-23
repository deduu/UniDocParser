// config.js
export const API_BASE_URL = window.API_BASE_URL || "";

// static/js/config.js  (ES module)

// Work out the +1 port, if any
// const { protocol, hostname, port } = window.location;

// let apiPort = "";
// if (port && /^\d+$/.test(port)) {
//   apiPort = ":" + (parseInt(port, 10) + 1);
// }

// const origin = `${protocol}//${hostname}${apiPort}`;

// // Make it available to non-module scripts **and** export for modules
// window.API_BASE_URL = origin;
// export const API_BASE_URL = origin;
