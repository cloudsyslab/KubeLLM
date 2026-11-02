import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "@artifact/App";
import { TooltipProvider } from "@/ui/tooltip";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <TooltipProvider delayDuration={200}>
      <App />
    </TooltipProvider>
  </StrictMode>,
);
