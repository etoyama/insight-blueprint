import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";

function App() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50">
      <h1 className="text-3xl font-bold text-gray-900">
        Hello from Insight Blueprint
      </h1>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
