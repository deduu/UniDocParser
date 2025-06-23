import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 8009, // <--- Change this to your desired port
    host: "0.0.0.0", // Optional: If you want to access from other devices on your network
  },
});
