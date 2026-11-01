import React from "react";
import { createRoot } from "react-dom/client";
import "@xyflow/react/dist/style.css";
import "./styles.css";
import { Room } from "./room";

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <Room />
  </React.StrictMode>,
);
